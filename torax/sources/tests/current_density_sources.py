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

"""Tests for current_density_sources."""

from absl.testing import absltest
from torax.sources import current_density_sources as cds
from torax.sources import source
from torax.sources import source_config
from torax.sources.tests import test_lib


class ECRHCurrentSourceTest(test_lib.SingleProfileSourceTestCase):
  """Tests for ECRHCurrentSource."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass(
        source_class=cds.ECRHCurrentSource,
        unsupported_types=[
            source_config.SourceType.MODEL_BASED,
        ],
        expected_affected_mesh_states=(
            source.AffectedMeshStateAttribute.PSI,
        ),
    )


class ICRHCurrentSourceTest(test_lib.SingleProfileSourceTestCase):
  """Tests for ICRHCurrentSource."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass(
        source_class=cds.ICRHCurrentSource,
        unsupported_types=[
            source_config.SourceType.MODEL_BASED,
        ],
        expected_affected_mesh_states=(
            source.AffectedMeshStateAttribute.PSI,
        ),
    )


class LHCurrentSourceTest(test_lib.SingleProfileSourceTestCase):
  """Tests for LHCurrentSource."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass(
        source_class=cds.LHCurrentSource,
        unsupported_types=[
            source_config.SourceType.MODEL_BASED,
        ],
        expected_affected_mesh_states=(
            source.AffectedMeshStateAttribute.PSI,
        ),
    )


class NBICurrentSourceTest(test_lib.SingleProfileSourceTestCase):
  """Tests for NBICurrentSource."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass(
        source_class=cds.NBICurrentSource,
        unsupported_types=[
            source_config.SourceType.MODEL_BASED,
        ],
        expected_affected_mesh_states=(
            source.AffectedMeshStateAttribute.PSI,
        ),
    )


if __name__ == '__main__':
  absltest.main()