# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# or in the "license" file accompanying this file. This file is distributed 
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either 
# express or implied. See the License for the specific language governing 
# permissions and limitations under the License.

import os
import json
import gym
import ray

from ray.tune.registry import register_env
from ray.rllib.models import ModelCatalog

from procgen_ray_launcher import ProcgenSageMakerRayLauncher

from ray_experiment_builder import RayExperimentBuilder

from utils.loader import load_algorithms, load_preprocessors
try:
    from custom.envs.procgen_env_wrapper import ProcgenEnvWrapper
except ModuleNotFoundError:
    from envs.procgen_env_wrapper import ProcgenEnvWrapper

class MyLauncher(ProcgenSageMakerRayLauncher):
    def register_env_creator(self):        
        register_env(
            "stacked_procgen_env",  # This should be different from procgen_env_wrapper
            lambda config: gym.wrappers.FrameStack(ProcgenEnvWrapper(config), 4)
        )

    def _get_ray_config(self):
        return {
            "ray_num_cpus": 16, # adjust based on selected instance type
            "ray_num_gpus": 0,
            "eager": False,
             "v": True, # requried for CW to catch the progress
        }

    def _get_rllib_config(self):
        return {
            "experiment_name": "training",
            "run": "PPO",
            "env": "procgen_env_wrapper",
            "stop": {
                # 'time_total_s': 60,
                'training_iteration': 15,
                },
            "checkpoint_freq": 1,
            "config": {
                "gamma": 0.999,
                "kl_coeff": 0.2,
                "lambda": 0.9,
                "lr": 0.0005,
                "num_workers": 15, # adjust based on ray_num_cpus
                "num_gpus": 0, # adjust based on ray_num_gpus
                "rollout_fragment_length": 140,
                "train_batch_size": 2048,
                "batch_mode": "truncate_episodes",
                "num_sgd_iter": 3,
                "use_pytorch": False,
                "model": {
                    "custom_model": "my_vision_network",
                    "conv_filters": [[16, [5, 5], 4], [32, [3, 3], 1], [256, [3, 3], 1]],
                },
                "env_config": {
                    # See https://github.com/AIcrowd/neurips2020-procgen-starter-kit/blob/master/experiments/procgen-starter-example.yaml#L34 for an explaination.
                    "env_name": "coinrun",
                    "num_levels": 0,
                    "start_level": 0,
                    "paint_vel_info": False,
                    "use_generated_assets": False,
                    "center_agent": True,
                    "use_sequential_levels": False,
                    "distribution_mode": "easy"
                }
            },
            # Uncomment if you want to use a config_file
            # "config_file": hyper_parameters["config_file"]
        }
    
    def register_algorithms_and_preprocessors(self):
        # TODO(annaluo@): register custom model via dynamic sourcing
        try:
            from custom.algorithms import CUSTOM_ALGORITHMS
            from custom.preprocessors import CUSTOM_PREPROCESSORS
            from custom.models.my_vision_network import MyVisionNetwork
        except ModuleNotFoundError:
            from algorithms import CUSTOM_ALGORITHMS
            from preprocessors import CUSTOM_PREPROCESSORS
            from models.my_vision_network import MyVisionNetwork

        load_algorithms(CUSTOM_ALGORITHMS)
        
        load_preprocessors(CUSTOM_PREPROCESSORS)
        ModelCatalog.register_custom_model("my_vision_network", MyVisionNetwork)

    def get_experiment_config(self):
        params = dict(self._get_ray_config())
        params.update(self._get_rllib_config())
        reb = RayExperimentBuilder(**params)
        return reb.get_experiment_definition()


if __name__ == "__main__":
    MyLauncher().train_main()
