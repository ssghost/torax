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

"""Classes for representing the problem geometry."""

from __future__ import annotations

import enum
import os

import chex
import jax
import jax.numpy as jnp
from torax import config as config_lib
from torax import config_slice
from torax import constants
from torax import geometry_loader
from torax import jax_utils
from torax import math_utils


@chex.dataclass(frozen=True)
class Grid1D:
  """Data structure defining a 1-D grid of cells with faces.

  Construct via `construct` classmethod.

  Attributes:
    nx: Number of cells.
    dx: Distance between cell centers.
    face_centers: Coordinates of face centers.
    cell_centers: Coordinates of cell centers.
  """

  nx: int
  dx: jax.Array
  face_centers: jax.Array
  cell_centers: jax.Array

  def __post_init__(self):
    jax_utils.assert_rank(self.nx, 0)
    jax_utils.assert_rank(self.dx, 0)
    jax_utils.assert_rank(self.face_centers, 1)
    jax_utils.assert_rank(self.cell_centers, 1)

  @classmethod
  def construct(cls, nx: int, dx: jnp.ndarray) -> Grid1D:
    """Constructs a Grid1D.

    Args:
      nx: Number of cells.
      dx: Distance between cell centers.

    Returns:
      grid: A Grid1D with the remaining fields filled in.
    """

    # Note: nx needs to be an int so that the shape `nx + 1` is not a Jax
    # tracer.

    return Grid1D(
        nx=nx,
        dx=dx,
        face_centers=jnp.linspace(0, nx * dx, nx + 1),
        cell_centers=jnp.linspace(dx * 0.5, (nx - 0.5) * dx, nx),
    )


def face_to_cell(face: jax.Array) -> jax.Array:
  """Infers cell values corresponding to a vector of face values.

  Reproduces the method in PINT, which is just linear interpolation
    between face values.

  Args:
    face: jnp.ndarray containing face values.

  Returns:
    cell: A jnp.ndarray containing cell values.
  """

  return 0.5 * (face[:-1] + face[1:])


@enum.unique
class GeometryType(enum.Enum):
  CIRCULAR = 0
  CHEASE = 1


# pylint: disable=invalid-name


@chex.dataclass(frozen=True)
class Geometry:
  """Describes the magnetic geometry."""
  geometry_type: int
  dr_norm: jax.Array
  dr: jax.Array
  mesh: Grid1D
  rmax: jnp.ndarray
  r_face_norm: jnp.ndarray
  r_norm: jnp.ndarray
  r_face: jnp.ndarray
  r: jnp.ndarray
  B0: jnp.ndarray
  volume: jnp.ndarray
  volume_face: jnp.ndarray
  area: jnp.ndarray
  area_face: jnp.ndarray
  vpr: jnp.ndarray
  vpr_face: jnp.ndarray
  spr_cell: jnp.ndarray
  spr_face: jnp.ndarray
  delta_face: jnp.ndarray
  G2: jnp.ndarray
  G2_face: jnp.ndarray
  g0: jnp.ndarray
  g0_face: jnp.ndarray
  g1: jnp.ndarray
  g1_face: jnp.ndarray
  g0_over_vpr_face: jnp.ndarray
  g1_over_vpr: jnp.ndarray
  g1_over_vpr_face: jnp.ndarray
  g1_over_vpr2: jnp.ndarray
  g1_over_vpr2_face: jnp.ndarray
  J: jnp.ndarray
  J_face: jnp.ndarray
  F: jnp.ndarray
  F_face: jnp.ndarray
  Rin: jnp.ndarray
  Rin_face: jnp.ndarray
  Rout: jnp.ndarray
  Rout_face: jnp.ndarray


@chex.dataclass(frozen=True)
class CircularGeometry(Geometry):
  kappa: jnp.ndarray
  kappa_face: jnp.ndarray
  volume_hires: jnp.ndarray
  area_hires: jnp.ndarray
  G2_hires: jnp.ndarray
  spr_hires: jnp.ndarray
  r_hires_norm: jnp.ndarray
  r_hires: jnp.ndarray
  kappa_hires: jnp.ndarray
  vpr_hires: jnp.ndarray


@chex.dataclass(frozen=True)
class CHEASEGeometry(Geometry):
  g2: jnp.ndarray
  g3: jnp.ndarray
  psi_chease: jnp.ndarray
  psi_from_chease_Ip: jnp.ndarray
  jtot: jnp.ndarray
  jtot_face: jnp.ndarray
  delta_upper_face: jnp.ndarray
  delta_lower_face: jnp.ndarray


# pylint: enable=invalid-name


def build_circular_geometry(
    config: config_lib.Config,
    kappa: float = 1.72,
    hires_fac: int = 4,
) -> CircularGeometry:
  """Constructs a CircularGeometry.

  This is the standard entrypoint for building a circular geometry, not
  CircularGeometry.__init__(). chex.dataclasses do not allow overriding __init__
  functions with different parameters than the attributes of the dataclass, so
  this builder function lives outside the class. When building a Fiddle config
  for this object, Fiddle-ify this function, not CircularGeometry.__init__.

  Args:
    config: General TORAX config.
    kappa: Elogination. Defaults to 1.72 for the ITER elongation, to
      approximately correct volume and area integral Jacobians.
    hires_fac: Grid refinement factor for poloidal flux <--> plasma current
      calculations.
  Returns:
    A CircularGeometry instance.
  """
  # assumes that r/Rmin = rho_norm where rho is the toroidal flux coordinate
  # r_norm coordinate is r/Rmin in circular, and rho_norm in standard
  # geometry (CHEASE/EQDSK)
  # Define mesh (Slab Uniform 1D with Jacobian = 1)
  dr_norm = jnp.array(1) / config.nr
  mesh = Grid1D.construct(nx=config.nr, dx=dr_norm)
  rmax = jnp.array(config.Rmin)
  # helper variables for mesh cells and faces
  # r coordinate of faces
  r_face_norm = mesh.face_centers
  # r coordinate of cell centers
  r_norm = mesh.cell_centers

  dr = dr_norm * rmax
  r_face = r_face_norm * rmax
  r = r_norm * rmax
  B0 = jnp.array(config.B0)  # pylint: disable=invalid-name

  # assumed elongation profile on cell grid
  kappa_param = kappa
  kappa = 1 + r_norm * (kappa_param - 1)
  # assumed elongation profile on cell grid
  kappa_face = 1 + r_face_norm * (kappa_param - 1)

  volume = 2 * jnp.pi**2 * config.Rmaj * r**2 * kappa
  volume_face = 2 * jnp.pi**2 * config.Rmaj * r_face**2 * kappa_face
  area = jnp.pi * r**2 * kappa
  area_face = jnp.pi * r_face**2 * kappa_face

  # V' for volume integrations
  vpr = (
      4 * jnp.pi**2 * config.Rmaj * r * kappa
      + volume / kappa * (kappa_param - 1) / rmax
  )
  vpr_face = (
      4 * jnp.pi**2 * config.Rmaj * r_face * kappa_face
      + volume_face / kappa_face * (kappa_param - 1) / rmax
  )
  # pylint: disable=invalid-name
  # S' for area integrals on cell grid
  spr_cell = (
      2 * jnp.pi * r * kappa + area / kappa * (kappa_param - 1) / rmax
  )
  spr_face = (
      2 * jnp.pi * r_face * kappa_face
      + area_face / kappa_face * (kappa_param - 1) / rmax
  )

  delta_face = jnp.zeros(len(r_face))

  # uses <1/R^2> with circular geometry
  G2 = vpr / (
      4 * jnp.pi**2 * config.Rmaj**2 * jnp.sqrt(1 - (r / config.Rmaj) ** 2)
  )

  # generate G2_face by hand
  G2_outer_face = vpr_face[-1] / (
      4
      * jnp.pi**2
      * config.Rmaj**2
      * jnp.sqrt(1 - (r_face[-1] / config.Rmaj) ** 2)
  )
  G2_outer_face = jnp.expand_dims(G2_outer_face, 0)
  G2_face = jnp.concatenate(
      (
          jnp.zeros((1,)),
          0.5 * (G2[:-1] + G2[1:]),
          G2_outer_face,
      ),
  )

  # g0 variable needed for general geometry form of transport equations
  g0 = vpr
  g0_face = vpr_face

  # g1 variable needed for general geometry form of transport equations
  g1 = vpr**2
  g1_face = vpr_face**2

  # simplifying assumption for now, for J=R*B/(R0*B0)
  J = jnp.ones(len(r))
  J_face = jnp.ones(len(r_face))
  # simplified (constant) version of the F=B*R function
  F = jnp.ones(len(r)) * config.Rmaj * B0
  F_face = jnp.ones(len(r_face)) * config.Rmaj * B0

  # High resolution versions for j (plasma current) and psi (poloidal flux)
  # manipulations. Needed for ad-hoc circular geometry only
  r_hires_norm = jnp.linspace(0, 1, config.nr * hires_fac)
  r_hires = r_hires_norm * rmax

  Rout = config.Rmaj + r
  Rout_face = config.Rmaj + r_face

  Rin = config.Rmaj - r
  Rin_face = config.Rmaj - r_face

  # assumed elongation profile on hires grid
  kappa_hires = 1 + r_hires_norm * (kappa_param - 1)

  volume_hires = 2 * jnp.pi**2 * config.Rmaj * r_hires**2 * kappa_hires
  area_hires = jnp.pi * r_hires**2 * kappa_hires

  # V' for volume integrations on hires grid
  vpr_hires = (
      4 * jnp.pi**2 * config.Rmaj * r_hires * kappa_hires
      + volume_hires / kappa_hires * (kappa_param - 1) / rmax
  )
  # S' for area integrals on hires grid
  spr_hires = (
      2 * jnp.pi * r_hires * kappa_hires
      + area_hires / kappa_hires * (kappa_param - 1) / rmax
  )

  # uses <1/R^2> with circular geometry
  denom = (
      4
      * jnp.pi**2
      * config.Rmaj**2
      * jnp.sqrt(1 - (r_hires / config.Rmaj) ** 2)
  )
  G2_hires = vpr_hires / denom

  # terms applied in transport equations and dt calculation.
  g1_over_vpr = g1 / vpr
  g1_over_vpr2 = g1 / vpr**2

  # initialization with zero to avoid div by zero on-axis (r=0)

  g0_over_vpr_face = g0_face[1:] / vpr_face[1:]
  g0_over_vpr_face = jnp.concatenate([jnp.ones(1), g0_over_vpr_face])

  g1_over_vpr_face = g1_face[1:] / vpr_face[1:]
  g1_over_vpr2_face = g1_face[1:] / vpr_face[1:] ** 2
  g1_over_vpr_face = jnp.concatenate([jnp.zeros(1), g1_over_vpr_face])
  g1_over_vpr2_face = jnp.concatenate([jnp.ones(1), g1_over_vpr2_face])

  return CircularGeometry(
      # Set the standard geometry params.
      geometry_type=GeometryType.CIRCULAR.value,
      dr_norm=dr_norm,
      dr=dr,
      mesh=mesh,
      rmax=rmax,
      r_face_norm=r_face_norm,
      r_norm=r_norm,
      r_face=r_face,
      r=r,
      B0=B0,
      volume=volume,
      volume_face=volume_face,
      area=area,
      area_face=area_face,
      vpr=vpr,
      vpr_face=vpr_face,
      spr_cell=spr_cell,
      spr_face=spr_face,
      delta_face=delta_face,
      G2=G2,
      G2_face=G2_face,
      g0=g0,
      g0_face=g0_face,
      g1=g1,
      g1_face=g1_face,
      g0_over_vpr_face=g0_over_vpr_face,
      g1_over_vpr=g1_over_vpr,
      g1_over_vpr_face=g1_over_vpr_face,
      g1_over_vpr2=g1_over_vpr2,
      g1_over_vpr2_face=g1_over_vpr2_face,
      J=J,
      J_face=J_face,
      F=F,
      F_face=F_face,
      Rin=Rin,
      Rin_face=Rin_face,
      Rout=Rout,
      Rout_face=Rout_face,
      # Set the circular geometry-specific params.
      kappa=kappa,
      kappa_face=kappa_face,
      volume_hires=volume_hires,
      area_hires=area_hires,
      G2_hires=G2_hires,
      spr_hires=spr_hires,
      r_hires_norm=r_hires_norm,
      r_hires=r_hires,
      kappa_hires=kappa_hires,
      vpr_hires=vpr_hires,
  )


# pylint: disable=invalid-name


def build_chease_geometry(
    config: config_lib.Config,
    geometry_dir: str | None = None,
    geometry_file: str = 'ITER_hybrid_citrin_equil_cheasedata.mat2cols',
    Ip_from_parameters: bool = True,
):
  """Constructs a geometry based on a CHEASE file.

  This is the standard entrypoint for building a CHEASE geometry, not
  CHEASEGeometry.__init__(). chex.dataclasses do not allow overriding __init__
  functions with different parameters than the attributes of the dataclass, so
  this builder function lives outside the class. When building a Fiddle config
  for this object, Fiddle-ify this function, not CHEASEGeometry.__init__.

  Args:
    config: General TORAX config.
    geometry_dir: Directory where to find the CHEASE file describing the
      magnetic geometry. If None, uses the environment variable
      TORAX_GEOMETRY_DIR if available. If that variable is not set and
      geometry_dir is not provided, then it defaults to another dir. See
      implementation.
    geometry_file: CHEASE file name.
    Ip_from_parameters: If True, take Ip from parameter file and rescale psi.
      Otherwise, Ip comes from CHEASE.
  Returns:
    A CHEASEGeometry instance based on the input file.
  """

  if geometry_dir is None:
    if 'TORAX_GEOMETRY_DIR' in os.environ:
      geometry_dir = os.environ['TORAX_GEOMETRY_DIR']
    else:
      geometry_dir = 'torax/data/third_party/geo'

  # initialize geometry from file
  chease_data = geometry_loader.initialize_CHEASE_dict(
      file_path=os.path.join(geometry_dir, geometry_file)
  )

  # TODO( b/326406367): incorporate time dependent geometry
  # build t_initial config_slice
  dynamic_config_slice = config_slice.build_dynamic_config_slice(config)

  # Prepare variables from CHEASE to be interpolated into our simulation
  # grid. CHEASE variables are normalized. Need to unnormalize them with
  # reference values poloidal flux and CHEASE-internal-calculated plasma
  # current.
  B0 = jnp.array(config.B0)  # pylint: disable=invalid-name
  psiunnormfactor = (config.Rmaj**2 * B0) * 2 * jnp.pi
  psi_chease = chease_data['PSIchease=psi/2pi'] * psiunnormfactor
  Ip_chease = (
      chease_data['Ipprofile']
      / constants.CONSTANTS.mu0
      * config.Rmaj
      * B0
  )

  # toroidal flux coordinate
  rho = chease_data['RHO_TOR=sqrt(Phi/pi/B0)'] * config.Rmaj
  rhon = chease_data['RHO_TOR_NORM']
  # midplane radii
  Rin = chease_data['R_INBOARD'] * config.Rmaj
  Rout = chease_data['R_OUTBOARD'] * config.Rmaj
  # toroidal field flux function
  J = chease_data['T=RBphi']

  # delta (triangularity). On face grid since only used in bootstrap current
  delta_upper_face = chease_data['delta_upper']
  delta_lower_face = chease_data['delta_bottom']

  # flux surface integrals of various geometry quantities
  C1 = (
      chease_data['Int(Rdlp/|grad(psi)|)=Int(Jdchi)']
      * config.Rmaj
      / B0
  )
  C2 = chease_data['<1/R**2>'] * C1 / config.Rmaj**2
  C3 = chease_data['<Bp**2>'] * C1 * B0**2
  C4 = chease_data['<|grad(psi)|**2>'] * C1 * (B0 * config.Rmaj) ** 2

  # derived quantities for transport equations and transformations

  # <\nabla V>
  g0 = (
      2
      * jnp.pi
      * chease_data['<|grad(psi)|>']
      * B0
      * config.Rmaj
      * C1
  )
  g1 = 4 * jnp.pi**2 * C1 * C4  # <(\nabla V)**2>
  g2 = 4 * jnp.pi**2 * C1 * C3  # <(\nabla V)**2 / R**2>
  g3 = C2[1:] / C1[1:]  # <1/R**2>
  g3 = jnp.concatenate((jnp.array([1 / Rin[0] ** 2]), g3))
  G2 = config.Rmaj / (16 * jnp.pi**4) * J[1:] * g2[1:] * g3[1:] / rho[1:]
  G2 = jnp.concatenate((jnp.zeros(1), G2))

  # make an alternative initial psi, self-consistent with CHEASE Ip profile
  # needed because CHEASE psi profile has noisy second derivatives
  dpsidrho = Ip_chease[1:] * constants.CONSTANTS.mu0 / G2[1:]
  dpsidrho = jnp.concatenate((jnp.zeros(1), dpsidrho))
  psi_from_chease_Ip = jnp.zeros(len(psi_chease))
  for i in range(1, len(psi_from_chease_Ip) + 1):
    psi_from_chease_Ip = psi_from_chease_Ip.at[i - 1].set(
        jax.scipy.integrate.trapezoid(dpsidrho[:i], rho[:i])
    )
  # set Ip-consistent psi derivative boundary condition (although will be
  # replaced later with an fvm constraint)
  psi_from_chease_Ip = psi_from_chease_Ip.at[-1].set(
      psi_from_chease_Ip[-2]
      + constants.CONSTANTS.mu0 * Ip_chease[-1] / G2[-1] * (rho[-1] - rho[-2])
  )

  # if Ip from parameter file, renormalize psi to match desired current
  if Ip_from_parameters:
    Ip_scale_factor = dynamic_config_slice.Ip * 1e6 / Ip_chease[-1]
    psi_from_chease_Ip *= Ip_scale_factor
  else:
    # This overwrites the config.Ip, even if it's time dependent, to be
    # consistent with the geometry file being processed
    config.Ip = Ip_chease[-1] / 1e6
    Ip_scale_factor = 1

  # volume, area, and dV/drho, dS/drho
  volume = chease_data['VOLUMEprofile'] * config.Rmaj**3
  area = chease_data['areaprofile'] * config.Rmaj**2
  vpr = math_utils.gradient(volume, rho)
  spr = math_utils.gradient(area, rho)
  # gradient boundary approximation not appropriate here
  vpr = vpr.at[0].set(0)
  spr = spr.at[0].set(0)

  # plasma current density
  jtot = (
      2
      * jnp.pi
      * config.Rmaj
      * math_utils.gradient(Ip_chease, volume)
      * Ip_scale_factor
  )

  # fill geometry structure
  # r_norm coordinate is rho_tor_norm
  dr_norm = jnp.array(1) / config.nr
  # normalized grid
  mesh = Grid1D.construct(nx=config.nr, dx=dr_norm)
  rmax = rho[-1]  # radius denormalization constant
  # helper variables for mesh cells and faces
  r_face_norm = mesh.face_centers
  r_norm = mesh.cell_centers

  dr = dr_norm * rmax
  r_face = r_face_norm * rmax
  r = r_norm * rmax

  interp_func = lambda x: jnp.interp(x, rhon, vpr)
  # V' for volume integrations on face grid
  vpr_face = interp_func(r_face_norm)
  # V' for volume integrations on cell grid
  vpr = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, spr)
  # S' for area integrals on face grid
  spr_face = interp_func(r_face_norm)
  # S' for area integrals on cell grid
  spr_cell = interp_func(r_norm)

  # triangularity on cell grid
  interp_func = lambda x: jnp.interp(x, rhon, delta_upper_face)
  delta_upper_face = interp_func(r_face_norm)
  interp_func = lambda x: jnp.interp(x, rhon, delta_lower_face)
  delta_lower_face = interp_func(r_face_norm)

  # average triangularity
  delta_face = 0.5*(delta_upper_face + delta_lower_face)

  interp_func = lambda x: jnp.interp(x, rhon, G2)
  G2_face = interp_func(r_face_norm)
  G2 = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, J)
  J_face = interp_func(r_face_norm)
  J = interp_func(r_norm)
  # simplified (constant) version of the F=B*R function
  F = J * config.Rmaj * B0
  # simplified (constant) version of the F=B*R function
  F_face = J_face * config.Rmaj * B0

  interp_func = lambda x: jnp.interp(x, rhon, psi_chease)
  psi_chease = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, psi_from_chease_Ip)
  psi_from_chease_Ip = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, jtot)
  jtot_face = interp_func(r_face_norm)
  jtot = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, Rin)
  Rin_face = interp_func(r_face_norm)
  Rin = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, Rout)
  Rout_face = interp_func(r_face_norm)
  Rout = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, g0)
  g0_face = interp_func(r_face_norm)
  g0 = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, g1)
  g1_face = interp_func(r_face_norm)
  g1 = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, g2)
  g2 = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, g3)
  g3 = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, volume)
  volume_face = interp_func(r_face_norm)
  volume = interp_func(r_norm)

  interp_func = lambda x: jnp.interp(x, rhon, area)
  area_face = interp_func(r_face_norm)
  area = interp_func(r_norm)

  # repeated terms in transport equations. Efficient to preevaluate

  g0_over_vpr_face = jnp.concatenate((
      jnp.ones(1),  # correct value is unity on-axis
      g0_face[1:] / vpr_face[1:],  # avoid div by zero on-axis
  ))

  g1_over_vpr = g1 / vpr
  g1_over_vpr2 = g1 / vpr**2
  g1_over_vpr_face = jnp.concatenate((
      jnp.zeros(1),  # correct value is zero on-axis
      g1_face[1:] / vpr_face[1:],  # avoid div by zero on-axis
  ))
  g1_over_vpr2_face = jnp.concatenate((
      jnp.ones(1),  # correct value is unity on-axis
      g1_face[1:] / vpr_face[1:] ** 2,  # avoid div by zero on-axis
  ))
  return CHEASEGeometry(
      geometry_type=GeometryType.CHEASE.value,
      dr_norm=dr_norm,
      dr=dr,
      mesh=mesh,
      rmax=rmax,
      r_face_norm=r_face_norm,
      r_norm=r_norm,
      r_face=r_face,
      r=r,
      B0=B0,
      volume=volume,
      volume_face=volume_face,
      area=area,
      area_face=area_face,
      vpr=vpr,
      vpr_face=vpr_face,
      spr_cell=spr_cell,
      spr_face=spr_face,
      delta_face=delta_face,
      G2=G2,
      G2_face=G2_face,
      g0=g0,
      g0_face=g0_face,
      g1=g1,
      g1_face=g1_face,
      g0_over_vpr_face=g0_over_vpr_face,
      g1_over_vpr=g1_over_vpr,
      g1_over_vpr_face=g1_over_vpr_face,
      g1_over_vpr2=g1_over_vpr2,
      g1_over_vpr2_face=g1_over_vpr2_face,
      J=J,
      J_face=J_face,
      F=F,
      F_face=F_face,
      Rin=Rin,
      Rin_face=Rin_face,
      Rout=Rout,
      Rout_face=Rout_face,
      # Set the CHEASE geometry-specific parameters.
      g2=g2,
      g3=g3,
      psi_chease=psi_chease,
      psi_from_chease_Ip=psi_from_chease_Ip,
      jtot=jtot,
      jtot_face=jtot_face,
      delta_upper_face=delta_upper_face,
      delta_lower_face=delta_lower_face,
  )

# pylint: enable=invalid-name