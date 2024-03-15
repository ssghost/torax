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

"""ITER baseline approximately based on Mantica PPCF 2021."""

from torax import config as config_lib
from torax import geometry
from torax import sim as sim_lib
from torax.sources import source_config
from torax.stepper import linear_theta_method


def get_config() -> config_lib.Config:
  return config_lib.Config(
      # simulation control
      t_final=10,  # length of simulation time in seconds
      # 1/multiplication factor for sigma (conductivity) to reduce current
      # diffusion timescale to be closer to heat diffusion timescale
      resistivity_mult=200,
      Ip=15,  # total plasma current in MA
      # physical inputs
      Rmaj=6.2,  # major radius (R) in meters
      Rmin=2.0,  # minor radius (a) in meters
      Ai=2.5,  # amu of main ion (if multiple isotope, make average)
      B0=5.3,  # Toroidal magnetic field on axis [T]
      Zeff=1.74,  # needed for qlknn and fusion power
      # effective impurity charge state assumed for matching dilution=0.862
      Zimp=6.3623,
      # boundary + initial conditions for T and n
      Ti_bound_left=15,  # initial condition ion temperature for r=0
      Ti_bound_right=0.238,  # boundary condition ion temperature for r=Rmin
      Te_bound_left=15,  # initial condition electron temperature for r=0
      Te_bound_right=0.238,  # boundary condition electron temperature at r=Rmin
      ne_bound_right=0.437,  # boundary condition density for r=Rmin
      # set initial condition density according to Greenwald fraction. Otherwise
      # from nbar
      set_fGW=True,
      fGW=0.77,  # original simulation goes up to ~0.92
      npeak=1.5,  # Peaking factor of density profile
      # external heat source parameters
      w=0.07280908366127758,  # Gaussian width in normalized radial coordinate
      # Source Gaussian central location in normalized r
      rsource=0.1383372589564274,
      Ptot=8.0e6,  # total heating (including accounting for radiation)
      el_heat_fraction=0.0,  # electron heating fraction
      # multiplier for ion-electron heat exchange term for sensitivity testing
      Qei_mult=1,
      # particle source parameters
      # pellets behave like a gas puff for this simulation with exponential
      # decay therefore use the "puff" structure for pellets
      # exponential decay length of gas puff ionization (normalized radial
      # coordinate)
      puff_decay_length=0.21,
      S_puff_tot=2.14e22,  # total pellet particles/s
      # Gaussian width of pellet deposition (normalized radial coordinate) in
      # continuous pellet model
      pellet_width=0.1,
      # Pellet source Gaussian central location (normalized radial coordinate)
      # in continuous pellet model
      pellet_deposition_location=0.85,
      # total pellet particles/s (continuous pellet model)
      S_pellet_tot=0.0e22,
      # NBI particle source Gaussian width (normalized radial coordinate)
      nbi_particle_width=0.25,
      # NBI particle source Gaussian central location (normalized radial
      # coordinate)
      nbi_deposition_location=0.5,
      S_nbi_tot=2.05e20,  # NBI total particle source
      # external current profiles
      fext=0.09,  # total "external" current fraction
      # width of "external" Gaussian current profile (normalized radial
      # coordinate)
      wext=0.25,
      # radius of "external" Gaussian current profile (normalized radial
      # coordinate)
      rext=0.35,
      # Multiplication factor for bootstrap current (note fbs~0.3 in original
      # simu)
      bootstrap_mult=1,
      # numerical (e.g. no. of grid points, other info needed by solver)
      nr=25,  # radial grid points
      maxdt=0.5,
      # multiplier in front of the base timestep dt=dx^2/(2*chi). Can likely be
      # increased further beyond this default
      dtmult=100,
      ion_heat_eq=True,
      el_heat_eq=True,
      current_eq=True,
      dens_eq=True,
      # internal boundary condition (pedestal)
      # do not set internal boundary condition if this is False
      set_pedestal=True,
      Tiped=5,  # ion pedestal top temperature in keV for Ti and Te
      Teped=5,  # electron pedestal top temperature in keV for Ti and Te
      neped=0.68,  # pedestal top electron density in units of nref
      Ped_top=0.93,  # set ped top location in normalized radius
      # effective source to dominate PDE in internal boundary condtion location
      # if T != Tped
      largeValue_T=1.0e10,
      # effective source to dominate density PDE in internal boundary condtion
      # location if n !=
      largeValue_n=1.0e8,
      transport=config_lib.TransportConfig(
          transport_model='qlknn',
          DVeff=True,
          coll_mult=0.25,
          # set inner core transport coefficients (ad-hoc MHD/EM transport)
          apply_inner_patch=True,
          De_inner=0.25,
          chii_inner=0.5,
          chie_inner=0.25,
          rho_inner=0.2,  # radius below which patch transport is applied
          # For QLKNN model
          include_ITG=True,  # to toggle ITG modes on or off
          include_TEM=True,  # to toggle ITG modes on or off
          include_ETG=True,  # to toggle ITG modes on or off
          # ensure that smag - alpha > -0.2 always, to compensate for no slab
          # modes
          avoid_big_negative_s=True,
          # minimum |R/Lne| below which effective V is used instead of effective
          # D
          An_min=0.05,
          ITG_flux_ratio_correction=1,
          # allowed chi and diffusivity bounds
          chimin=0.05,  # minimum chi
          chimax=100,  # maximum chi (can be helpful for stability)
          Demin=0.05,  # minimum electron diffusivity
      ),
      solver=config_lib.SolverConfig(
          predictor_corrector=False,
          coupling_use_explicit_source=True,
          convection_dirichlet_mode='semi-implicit',
          convection_neumann_mode='semi-implicit',
          use_pereverzev=True,
          chi_per=20,
          d_per=10,
      ),
      sources=dict(
          fusion_heat_source=source_config.SourceConfig(
              source_type=source_config.SourceType.MODEL_BASED,
          ),
          ohmic_heat_source=source_config.SourceConfig(
              source_type=source_config.SourceType.ZERO,
          ),
      ),
  )


def get_geometry(config: config_lib.Config) -> geometry.Geometry:
  return geometry.build_chease_geometry(
      config,
      geometry_file='ITER_hybrid_citrin_equil_cheasedata.mat2cols',
      Ip_from_parameters=True,
  )


def get_sim() -> sim_lib.Sim:
  # This approach is currently lightweight because so many objects require
  # config for construction, but over time we expect to transition to most
  # config taking place via constructor args in this function.
  config = get_config()
  geo = get_geometry(config)
  return sim_lib.build_sim_from_config(
      config, geo, linear_theta_method.LinearThetaMethod
  )