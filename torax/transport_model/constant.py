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

"""The ConstantTransportModel class.

A simple model assuming constant transport.
"""

from jax import numpy as jnp
from torax import config_slice
from torax import geometry
from torax import state as state_module
from torax.transport_model import transport_model


class ConstantTransportModel(transport_model.TransportModel):
  """Calculates various coefficients related to particle transport."""

  def _call_implementation(
      self,
      dynamic_config_slice: config_slice.DynamicConfigSlice,
      geo: geometry.Geometry,
      state: state_module.State,
  ) -> transport_model.TransportCoeffs:
    del state  # Not needed for this transport model
    return transport_model.TransportCoeffs(
        chi_face_ion=dynamic_config_slice.transport.chii_const
        * jnp.ones_like(geo.r_face),
        chi_face_el=dynamic_config_slice.transport.chie_const
        * jnp.ones_like(geo.r_face),
        d_face_el=dynamic_config_slice.transport.De_const
        * jnp.ones_like(geo.r_face),
        v_face_el=dynamic_config_slice.transport.Ve_const
        * jnp.ones_like(geo.r_face),
    )