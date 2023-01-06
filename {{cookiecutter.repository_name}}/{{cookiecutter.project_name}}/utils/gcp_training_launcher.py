import dataclasses
import inspect
import logging
import time
import typing as t

from dataclasses import dataclass

from google.cloud import compute_v1

from {{cookiecutter.project_name}}.config_schemas.infrastructure.infrastructure_schema import InfrastructureConfig
from {{cookiecutter.project_name}}.config_schemas.infrastructure.job_info_schema import JobInfo
from {{cookiecutter.project_name}}.config_schemas.infrastructure.vm_config_schema import VMMode, VMTemplateConfig
from {{cookiecutter.project_name}}.utils.gcp_utils import get_disk_image, wait_for_extended_operation
from {{cookiecutter.project_name}}.utils.utils import get_logger

GCP_TRAINING_LAUNCHER_LOGGER = get_logger(__name__)


@dataclass
class VMMetadata:
    job_id: str
    task_id: str
    cluster_id: str
    gcp_docker_registry_url: str
    base_path: str
    zone: str
    python_hash_seed: int
    node_count: int = 1
    additional_metadata: t.Mapping[str, str] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, t.Any]:
        all_fields = dataclasses.asdict(self)
        del all_fields["additional_metadata"]
        for k, v in self.additional_metadata.items():
            all_fields[k] = v
        return all_fields


@dataclass
class VMInstanceGroupConfig:
    project_id: str
    cluster_id: str
    instance_template_url: str
    size: int
    zone: str


@dataclass
class TrainingInfo:
    project_id: str
    zone: str
    job_info: JobInfo
    cluster_id: str
    base_path: str
    instance_ids: list[int]

    def get_job_info_message(self) -> str:
        (
            instance_ids_regex,
            log_viewer_url,
            monitoring_group_create_url,
            train_cluster_url,
        ) = self._get_job_tracking_links()

        run_description = f"""
            Experiment data: {self.base_path}
            Deployed training cluster: {train_cluster_url}
            Experiment logs (python): {log_viewer_url}
            Create monitoring group: {monitoring_group_create_url}

            if something goes wrong type in log viewer query field:
            ```
            resource.type="gce_instance"
            logName="projects/{self.project_id}/logs/GCEMetadataScripts"
            resource.labels.instance_id={instance_ids_regex}
            ```
        """
        return inspect.cleandoc(run_description)

    def print_job_info(self) -> None:
        print(f"============ training {self.job_info.job_id} details ============")
        print(self.get_job_info_message())

    def _get_job_tracking_links(self) -> tuple[str, str, str, str]:
        instance_ids = [str(id) for id in self.instance_ids]
        instance_ids_regex = " OR ".join(instance_ids)
        instance_ids_url = "%20OR%20".join(instance_ids)
        train_cluster_url = f"https://console.cloud.google.com/compute/instanceGroups/details/{self.zone}/{self.cluster_id}?project={self.project_id}"
        log_viewer_url = f"https://console.cloud.google.com/logs/query;query=resource.type%3D%22gce_instance%22%0Aresource.labels.instance_id%3D%2528{instance_ids_url}%2529?project={self.project_id}"
        monitoring_group_create_url = (
            f"https://console.cloud.google.com/monitoring/groups/create?project=${self.project_id}"
        )
        return instance_ids_regex, log_viewer_url, monitoring_group_create_url, train_cluster_url


class DistributedJobLauncher:
    def __init__(self, project_id: str, zone: str):
        super().__init__()
        self.project_id = project_id
        self.zone = zone

    def run_remote_training(self, infra_cfg: InfrastructureConfig) -> TrainingInfo:
        gcp_docker_registry_url = f"{{cookiecutter.gcp_docker_registry}}-docker.pkg.dev/{infra_cfg.project_id}/{{cookiecutter.project_name}}/{{cookiecutter.project_name}}-model:{infra_cfg.vm_config.docker_image_tag}"
        cluster_id = f"{infra_cfg.job_info.job_id}-t".lower()
        base_path = infra_cfg.base_path()

        vm_metadata = VMMetadata(
            job_id=infra_cfg.job_info.job_id,
            task_id=infra_cfg.job_info.task_id,
            cluster_id=cluster_id,
            gcp_docker_registry_url=gcp_docker_registry_url,
            base_path=base_path,
            zone=infra_cfg.zone,
            python_hash_seed=infra_cfg.python_hash_seed,
            node_count=infra_cfg.vm_config.node_count,
        )
        logging.debug(f"{vm_metadata=}")

        logging.info(f"Creating VM template: {cluster_id}...")
        vm_template = self._create_template(cluster_id, infra_cfg.vm_config, vm_metadata)
        logging.debug(f"{vm_template=}")

        logging.info(
            f"Creating instance group {cluster_id} (nodes: {infra_cfg.vm_config.node_count} x {infra_cfg.vm_config.machine.machine_type}, {infra_cfg.vm_config.machine.accelerator_count} x {infra_cfg.vm_config.machine.accelerator_type} GPUs per node)..."
        )
        instance_group_config = VMInstanceGroupConfig(
            project_id=infra_cfg.project_id,
            cluster_id=cluster_id,
            instance_template_url=vm_template.self_link,
            size=infra_cfg.vm_config.node_count,
            zone=infra_cfg.zone,
        )
        instance_group = self._create_instance_group(instance_group_config)
        logging.debug(f"{instance_group=}")

        instance_ids = self._get_instance_ids(cluster_id, infra_cfg.vm_config.node_count)
        logging.debug(f"{instance_ids=}")

        training_info = TrainingInfo(
            infra_cfg.project_id,
            infra_cfg.zone,
            infra_cfg.job_info,
            cluster_id,
            base_path,
            instance_ids,
        )
        return training_info

    def list_instances_in_group(
        self, cluster_id: str
    ) -> compute_v1.services.instance_group_managers.pagers.ListManagedInstancesPager:

        instance_group_managers_client = compute_v1.InstanceGroupManagersClient()
        pager = instance_group_managers_client.list_managed_instances(
            project=self.project_id, instance_group_manager=cluster_id, zone=self.zone
        )

        return pager

    def _create_template(
        self, name: str, config: VMTemplateConfig, vm_metadata: VMMetadata
    ) -> compute_v1.InstanceTemplate:
        template = compute_v1.InstanceTemplate()
        template.name = name

        boot_disk = self._create_boot_disk(config)
        if boot_disk:
            template.properties.disks = [boot_disk]

        for disk_name in config.disks:
            disk = compute_v1.AttachedDisk(
                auto_delete=False, boot=False, mode="READ_ONLY", device_name=disk_name, source=disk_name
            )
            template.properties.disks.append(disk)

        network_interface = self._create_network_interface(config.network, config.subnetwork)
        template.properties.network_interfaces = [network_interface]

        template.properties.machine_type = config.machine.machine_type
        template.properties.guest_accelerators = [
            compute_v1.AcceleratorConfig(
                accelerator_type=config.machine.accelerator_type, accelerator_count=config.machine.accelerator_count
            )
        ]
        template.properties.service_accounts = [compute_v1.ServiceAccount(email="default", scopes=config.scopes)]
        template.properties.labels = config.labels

        if config.machine.train_machine_mode == VMMode.PREEMPTIBLE:
            logging.info("Using PREEMPTIBLE mode")
            template.properties.scheduling = compute_v1.Scheduling(preemptible=True)
        elif config.machine.train_machine_mode == VMMode.SPOT:
            logging.info("Using SPOT mode")
            template.properties.scheduling = compute_v1.Scheduling(provisioning_model=compute_v1.Scheduling.ProvisioningModel.SPOT.name)  # type: ignore
        elif config.machine.train_machine_mode == VMMode.STANDARD:
            logging.info("Using STANDARD mode")
            # No special configuration needed
            pass
        else:
            raise RuntimeError(f"Unsupported train_machine_mode={config.machine.train_machine_mode}")

        startup_script = self._load_startup_script(config.startup_script_path)
        template.properties.metadata.items.append(compute_v1.Items(key="startup-script", value=startup_script))

        if config.disks:
            template.properties.metadata.items.append(compute_v1.Items(key="disks", value="\n".join(config.disks)))

        for k, v in vm_metadata.to_dict().items():
            template.properties.metadata.items.append(compute_v1.Items(key=k, value=str(v)))

        template_client = compute_v1.InstanceTemplatesClient()
        operation = template_client.insert(project=config.project_id, instance_template_resource=template)

        wait_for_extended_operation(operation, "instance template creation")

        return template_client.get(project=config.project_id, instance_template=name)

    def _load_startup_script(self, startup_script_path: str) -> str:
        with open(startup_script_path, "r") as f:
            startup_script = f.read()
        return startup_script

    def _create_instance_group(self, config: VMInstanceGroupConfig) -> compute_v1.InstanceGroupManager:

        instance_group_manager_resource = compute_v1.InstanceGroupManager(
            name=config.cluster_id,
            base_instance_name=config.cluster_id,
            instance_template=config.instance_template_url,
            target_size=config.size,
        )

        instance_group_managers_client = compute_v1.InstanceGroupManagersClient()
        operation = instance_group_managers_client.insert(
            project=config.project_id, instance_group_manager_resource=instance_group_manager_resource, zone=config.zone
        )

        wait_for_extended_operation(operation, "managed instance group creation")

        return instance_group_managers_client.get(
            project=config.project_id, instance_group_manager=config.cluster_id, zone=config.zone
        )

    def _create_network_interface(self, network: str, subnetwork: str) -> compute_v1.NetworkInterface:
        network_interface = compute_v1.NetworkInterface()
        network_interface.name = "nic0"
        network_interface.network = network
        network_interface.subnetwork = subnetwork
        return network_interface

    def _create_boot_disk(self, config: VMTemplateConfig) -> compute_v1.AttachedDisk:
        boot_disk = compute_v1.AttachedDisk()
        boot_disk_initialize_params = compute_v1.AttachedDiskInitializeParams()
        boot_disk_image = get_disk_image(config.disk_image_project_id, config.disk_image_name)
        boot_disk_initialize_params.source_image = boot_disk_image.self_link
        boot_disk_initialize_params.disk_size_gb = config.disk_size_gb
        boot_disk_initialize_params.labels = config.labels
        boot_disk.initialize_params = boot_disk_initialize_params
        boot_disk.auto_delete = True
        boot_disk.boot = True
        boot_disk.device_name = config.boot_disk_name
        return boot_disk

    def _get_instance_ids(self, cluster_id: str, node_count: int) -> list[int]:
        instance_ids = set()
        attempt = 0
        max_attempts = 10
        base_sleep_time = 1.5
        while attempt < max_attempts:
            logging.info(f"Waiting for instances (attempt {attempt})...")
            pager = self.list_instances_in_group(cluster_id)
            for instance in pager:
                if instance.id:
                    logging.info(f"Instance {instance.id} ready")
                    instance_ids.add(instance.id)
            if len(instance_ids) >= node_count:
                break
            time.sleep(pow(base_sleep_time, attempt))
            attempt += 1
        return list(instance_ids)
