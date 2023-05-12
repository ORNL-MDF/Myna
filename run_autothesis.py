import autothesis.main
import autothesis.plot
import autothesis.simulation as simulation
import autothesis.peregrine as peregrine
import autothesis.parser as parser
import os
import numpy as np

def run_autothesis(settings):

    # [WIP]: Need to figure out how to mount Savitar drive on Unix system
    #        or how to do the file copies to/from Savitar using SFTP or the like.
    #        Currently using a local copy of Peregrine directory structure
    #        for the demo case.
    
    sim = autothesis.main.Simulation()
    sim.peregrine_path = settings["Peregrine"]["build_path"]
    sim.executable_path = settings["3DThesis"]["executable"]
    sim.input_dir = settings["3DThesis"]["input_dir_path"]
    sim.input_file = settings["3DThesis"]["input_file_path"]
    sim.material_dir = settings["3DThesis"]["material_database_path"]
    sim.output_dir = settings["3DThesis"]["output_dir_path"]

    # Iterate through each part, all layers
    for part in settings["3DThesis"]["parts"]:
        print(f'Part number {part["part_number"]}, layers {part["layer_start"]} to {part["layer_end"]}')
        for layer in np.arange(part["layer_start"],part["layer_end"]+1):
            
            # Set up simulation files
            peregrine.copy_scan(buildpath=sim.peregrine_path,
                                partnumber=part["part_number"],
                                layernumber=layer,
                                output_file=os.path.join(sim.input_dir, "Path.txt"))
            peregrine.load_material_data(buildpath=sim.peregrine_path,
                                         DatabasePath=sim.material_dir,
                                         output_file=os.path.join(sim.input_dir, "Material.txt"))
            peregrine.load_beam_data(buildpath=sim.peregrine_path,
                                     partnumber=part["part_number"],
                                     output_file=os.path.join(sim.input_dir, "Beam.txt"))
            
            # Run simulation
            output_path = simulation.run(case_directory=os.path.abspath(sim.input_dir),
                                         input_file=sim.input_file,
                                         exec_path=sim.executable_path)

            # Store the simulation results
            name = f'Part{part["part_number"]:02}.Layer{layer:04}.csv'
            result_file = parser.copy_simulation_result(new_file=os.path.join(sim.output_dir, name), 
                                                        result_file=output_path)
            
            # Upload to Peregrine, if requested
            if settings["3DThesis"]["Peregrine"]["upload"] == True:
                for var in settings["3DThesis"]["Peregrine"]["variables"]:
                    peregrine.upload_results(buildpath=sim.peregrine_path,
                                             partnumber=part["part_number"],
                                             layernumber=layer,
                                             result_file=result_file,
                                             var=var["varname"],
                                             var_name=var["exportname"],
                                             var_unit=var["unit"],
                                             datapath=os.path.join(
                                                sim.peregrine_path,
                                                "registered",
                                                var["exportname"]
                                                )
                                            )

    return result_file
