# Copyright 2024 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The FixedTimeStepCalculator class.

Steps through time using a constant time step.
"""

from typing import Union

import jax
from jax import numpy as jnp
from torax import config_slice
from torax import geometry
from torax import state as state_module
from torax.time_step_calculator import time_step_calculator
from torax.transport_model import transport_model as transport_model_lib

# Dummy state and type for compatibility with time_step_calculator base class
STATE = None
State = type(STATE)


class FixedTimeStepCalculator(time_step_calculator.TimeStepCalculator[State]):
  """TimeStepCalculator based on constant time steps.

  Attributes:
    config: General configuration parameters.
  """

  def initial_state(self):
    return STATE

  def not_done(
      self,
      t: Union[float, jax.Array],
      dynamic_config_slice: config_slice.DynamicConfigSlice,
      state: State,
  ) -> Union[bool, jax.Array]:
    """Returns True if iteration not done (t < config.t_final)."""
    return t < dynamic_config_slice.t_final

  def next_dt(
      self,
      dynamic_config_slice: config_slice.DynamicConfigSlice,
      geo: geometry.Geometry,
      sim_state: state_module.State,
      time_step_calculator_state: State,
      transport_model: transport_model_lib.TransportModel,
  ) -> tuple[jax.Array, State]:
    """Calculates the next time step duration.

    Args:
      dynamic_config_slice: Input config parameters that can change without
        triggering a JAX recompilation.
      geo: Geometry for the tokamak being simulated.
      sim_state: Current state of the tokamak.
      time_step_calculator_state: None, for compatibility with
        TimeStepCalculator base class.
      transport_model: Used to calculate chi, which determines maximum step
        size.

    Returns:
      dt: Scalar time step duration.
    """

    dt = jnp.array(dynamic_config_slice.fixed_dt)

    return dt, STATE