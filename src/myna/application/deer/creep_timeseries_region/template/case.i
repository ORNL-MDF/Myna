# This input file uses the HIT file format
# The [pyhit](https://mooseframework.inl.gov/python/source/pyhit/pyhit.html)
# package provides a Python interface for interacting with the file

# Constants
tramp = 1

# Variables updated by Myna app
load = {LOAD}
RVE_length = {RVE_LENGTH}

[Mesh]
  [base]
    type = FileMeshGenerator
  []
  [rename]
    type = RenameBoundaryGenerator
    input = base
    old_boundary = '1 2 3 4 5 6'
    new_boundary = 'x0 x1 y0 y1 z0 z1'
  []
  [breakmesh]
    input = rename
    type = BreakMeshByBlockGenerator
  []
  # [add_side_sets]
  #   # adding sidesets to apply boundary conditions
  #   input = breakmesh
  #   type = SideSetsFromNormalsGenerator
  #   normals = '-1  0  0
  #               1  0  0
  #               0 -1  0
  #               0  1  0
  #               0  0 -1
  #               0  0  1'

  #   new_boundary = 'x0 x1 y0 y1 z0 z1'
  #   fixed_normal = true
  # []
  use_displaced_mesh = false
[]


[GlobalParams]
  displacements = 'disp_x disp_y disp_z'
[]

[AuxVariables]
  [D]
    family = MONOMIAL
    order = CONSTANT
  []
[]

[AuxKernels]
  [D]
    type = MaterialRealAux
    boundary = 'interface'
    property = damage
    execute_on = 'TIMESTEP_END'
    variable = D
    check_boundary_restricted = false #this is important
  []
[]

[Physics]
  [SolidMechanics]
    [QuasiStatic]
      [all]
        strain = FINITE
        new_system = true
        formulation = TOTAL
        add_variables = true
        volumetric_locking_correction = true
        generate_output = 'cauchy_stress_xx cauchy_stress_yy cauchy_stress_zz cauchy_stress_yz cauchy_stress_xz cauchy_stress_xy '
                          'mechanical_strain_xx mechanical_strain_yy mechanical_strain_zz mechanical_strain_yz mechanical_strain_xz mechanical_strain_xy'
      []
    []
  []
[]
[Physics/SolidMechanics/CohesiveZone]
  [./czm_ik1]
    boundary = 'interface'
    strain = FINITE # use finite strins, total lagrangian formulation
    generate_output='traction_x traction_y traction_z jump_x jump_y jump_z normal_traction tangent_traction normal_jump tangent_jump' #output traction and jump
  [../]
[]

[UserObjects]
  [./euler_angle_file]
    type = PropertyReadFile
    nprop = 3
    use_zero_based_block_indexing = false
  [../]
[]

[Materials]
  [stress]
  # define the bulk material model, euler angles for each grain come from the `euler_angle_file` UserObjects
    type = NEMLCrystalPlasticity
    model = "cpdeformation"
    large_kinematics = true
    euler_angle_reader = euler_angle_file
  []
  # [GB_props]
  #   type = GenericConstantMaterial
  #   prop_names = 'a0 b0 D_GB E G w eta_s T0 FN Nc'
  #   prop_values = '4e-5 5.9e-2 1e-17 150e3 58.3657588e3 0.0113842 1e20 200 1.8e5 0.91'
  #   boundary = 'interface'
  # []
  [GB]
    type = GrainBoundaryCavitation
    a0 = a0
    b0 = b0
    psi = 70
    n = 5
    P = 69444.439 # (E_penalty_minus_thickenss - 1)/(w^2)
    gamma = 2
    eps = 1e-6
    fixed_triaxiality = LOW
    growth_due_to_diffusion = true
    growth_due_to_creep = true
    boundary = 'interface'
  []
[]


[BCs]
  [x0]
    type = DirichletBC
    variable = disp_x
    boundary = x0
    value = 0.0
  []
  [y0]
    type = DirichletBC
    variable = disp_y
    boundary = y0
    value = 0.0
  []
  [z0]
    type = DirichletBC
    variable = disp_z
    boundary = z0
    value = 0.0
  []
  [{LOADDIR}1]
    type = FunctionNeumannBC
    boundary = {LOADDIR}1
    function = applied_load
    variable = disp_{LOADDIR}
  []
[]

[Functions]
  [applied_load]
 type = PiecewiseLinear
    x = '0 ${tramp} 1e7'
    y = '0 ${load} ${load}'
  []
[]

[Constraints]
  [x1]
    type = EqualValueBoundaryConstraint
    variable = disp_x
    secondary = 'x1'
    penalty = 1e7
  []
  [y1]
    type = EqualValueBoundaryConstraint
    variable = disp_y
    secondary = 'y1'
    penalty = 1e7
  []
  [z1]
    type = EqualValueBoundaryConstraint
    variable = disp_z
    secondary = 'z1'
    penalty = 1e7
  []
[]

[Preconditioning]
  [./SMP]
    type = SMP
    full = true
  [../]
[]

[Postprocessors]
  [a]
    type = SideAverageMaterialProperty
    boundary = 'interface'
    property = average_cavity_radius
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [b]
    type = SideAverageMaterialProperty
    boundary = 'interface'
    property = average_cavity_half_spacing
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [D_min]
    type = SideExtremeMaterialProperty
    boundary = 'interface'
    mat_prop = damage
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [D_max]
    type = SideExtremeMaterialProperty
    boundary = 'interface'
    mat_prop = damage
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [D_avg]
    type = SideAverageMaterialProperty
    boundary = 'interface'
    property = damage
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [avg_disp_{LOADDIR}]
    type = SideAverageValue
    variable = disp_{LOADDIR}
    boundary = {LOADDIR}1
    execute_on = 'INITIAL TIMESTEP_END'
    outputs = none
  []
  [strain]
    type = ParsedPostprocessor
    pp_names = 'avg_disp_{LOADDIR}'
    expression = 'avg_disp_{LOADDIR} / ${RVE_length}'
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [delta_strain]
    type = ChangeOverTimePostprocessor
    postprocessor = strain
    execute_on = 'INITIAL TIMESTEP_END'
    outputs = none
  []
  [dt]
    type = TimestepSize
    execute_on = 'INITIAL TIMESTEP_END'
    outputs = none
  []
  [strain_rate]
    type = ParsedPostprocessor
    pp_names = 'delta_strain dt'
    expression = 'delta_strain / dt'
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]

[Executioner]
  type = Transient

  solve_type = 'newton'

  petsc_options = '-snes_converged_reason -ksp_converged_reason'
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_package -ksp_gmres_restart -pc_hypre_boomeramg_strong_threshold -pc_hypre_boomeramg_interp_type -pc_hypre_boomeramg_coarsen_type -pc_hypre_boomeramg_agg_nl -pc_hypre_boomeramg_agg_num_paths -pc_hypre_boomeramg_truncfactor'
  petsc_options_value = 'hypre boomeramg 301 0.7 ext+i HMIS 4 2 0.4'


  line_search = none
  automatic_scaling = true
  l_max_its = 300
  # l_tol = 1e-7
  nl_max_its = 15
  nl_rel_tol = 1e-6
  nl_abs_tol = 1e-6
  nl_forced_its = 1
  n_max_nonlinear_pingpong = 1
  dtmin = 1e-8
  dtmax = 1e4
  end_time = 3600000

  [./Predictor]
    type = SimplePredictor
    scale = 1.0
    skip_after_failed_timestep = true
  [../]

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-3
    growth_factor = 2
    cutback_factor = 0.5
    cutback_factor_at_failure = 0.1
    optimal_iterations = 8
    iteration_window = 1
    linear_iteration_ratio = 1000000000
  []
[]

[Outputs]
  print_linear_residuals = false
  [./checkpoint]
    type = Checkpoint
    num_files = 2
    time_step_interval = 4
    file_base = wCreep_checkpoint
  [../]
  [./out]
    type = Exodus
    file_base = {OUTPUT_NAME}
    time_step_interval = 1
  [../]
  [./out_csv]
    type = CSV
    file_base = {OUTPUT_NAME}
  [../]
[]
