
# Configuration Files

In this project [hydra-core](https://hydra.cc/docs/intro/) library is used to handle configuration files.
It is strongly adviced to:

1. Read [OmegaConf](https://omegaconf.readthedocs.io/en/2.2_branch/) documentation (because hydra uses it internally)
2. Read [Hydra Tutorial](https://hydra.cc/docs/tutorials/intro/)

before you go any further.

## Config Structure

Here is how our config structure looks like (currently it might be slightly different):

```
.
├── README.md
├── __init__.py
├── config.yaml
├── experiment
├── hydra
│   └── job_logging
│       └── custom.yaml
├── loss_function
│   ├── cross_entropy.yaml
│   └── focal_loss.yaml
├── mlflow
│   ├── clip.yaml
│   ├── default.yaml
│   └── test.yaml
├── model
│   ├── adapter
│   │   ├── some_adapter_name.yaml
│   │   └── some_other_adapter_name.yaml
│   ├── backbone
│   │   ├── language
│   │   │   └── bert.yaml
│   │   └── vision
│   │       ├── efficient_net.yaml
│   │       ├── resnet.yaml
│   │       └── vit32.yaml
│   ├── clip_model.yaml
│   ├── fuser
│   └── head
│       ├── multi_label_binary_cross_entropy.yaml
│       └── softmax.yaml
├── reproducibility
│   ├── default.yaml
│   └── test.yaml
├── optimizer
│   ├── adam.yaml
└── training
└── test.yaml

```

### How to add new config files?
Let's say currently you are running your training using Adam optimizer, and you would like to experiment with SGD.
In order to do that you can add a new config file called `sgd.yaml` under `optimizer` config group, and in the main
config choose this new config file as the new optimizer. You can also select different parts of the config using command line
arguments:

```bash
python ./{{cookiecutter.project_name}}/train.py optimizer=adam
# or, if you now have sgd.yaml, you can also do:
python ./{{cookiecutter.project_name}}/train.py optimizer=sgd 
```

When you need to modify more than 1 sub-section in the main config file, instead of doing this:

```bash
python ./{{cookiecutter.project_name}}/train.py optimizer=adam model.backbone.language=bert model.backbone.vision=efficient_net model.adapter=some_adapter_name
```

create a `.yaml` file in `experiment` config group, and override the parts of the config you would like to modify. As an example:

```yaml
# ./{{cookiecutter.project_name}}/configs/experiment/my_experiment.yaml

# @package _global_
defaults:
  - override /optimizer: adam
  - override /model/backbone/language: bert
  - override /model/backbone/vision: efficient_net
  - override /model.apater: some_adapter_name
```

and then:

```bash
python ./{{cookiecutter.project_name}}/train.py +experiment=my_experiment
```

If you would like to learn more about experimenting you can check [this](https://hydra.cc/docs/patterns/configuring_experiments/) link out.


### How to select a list of config files from a config group?

Unfortunatelly, `OmegaConf` currently doesn't support selecting multiple config files from a config group:

```yaml
defaults:
  - callbacks:
    - callback1
    - callback2
```

This doesn't work. This feature will be brought in the future, however, for now we need a work around.
In order to achieve this, you need 2 fields in your Config Schema:

```python
@dataclasses
class SomeClassConfig:
  callbacks: Any
  _callbacks_dict: dict[str, CallbackConfig]
```

Then you can do this in your config:

```yaml
defaults:
  - callbacks@_callbacks_dict.cb1: callback1
  - callbacks@_callbacks_dict.cb2: callback2

callbacks: ${oc.dict.values:._callbacks_dict}
```

Unfortunately we need this work around for now, but it works.


## Config Schemas

Whenever you need to add a new configuration file, you need to create a `schema` for that at appropriate location in
`{{cookiecutter.project_name}}/config_schemas/` folder. The best way to learn how to do it is to check examples in this folder.


### DictExpansionMixin

If you want the `dataclass` you wrote (as a part of the config schema) support dictionary expansion syntax (`**my_class`),
you can use `DictExpansionMixin` in your schema.

```python
class MyOptimizerConfig(DictExpansionMixin):
  ...
```
