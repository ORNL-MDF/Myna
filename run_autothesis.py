import autothesis.main
import autothesis.plot
import autothesis.simulation as simulation
import autothesis.peregrine as peregrine
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

    # Iterate through each part, all layers
    for part in settings["3DThesis"]["parts"]:
        print(f'Part number {part["part_number"]}, layers {part["layer_start"]} to {part["layer_end"]}')
        for layer in np.arange(part["layer_start"],part["layer_end"]+1):
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
            output_path = simulation.run(case_directory=os.path.abspath(sim.input_dir),
                                         input_file=sim.input_file,
                                         exec_path=sim.executable_path)

    return output_path

'''
    layers = [50]
    parts = [20]

    
    # Generate results
    result_files = autothesis.main.run_parts_layers(buildpath, 
                                                    layers, 
                                                    parts,
                                                    outdir=os.path.join("demo_case","Outputs"),
                                                    upload=False)
    
    return result_files

    # Plot results
    for result_file in result_files:
        print("Plotting result: ", result_file)
        autothesis.plot.scatter_top_surface(result_file, 
                                            vars=["G", "V"])
    
    # Convert format (to .npz and .png) and upload results to Peregrine
    for result_file in result_files:
        print("Uploading result to Peregrine: ", result_file)
        part = int(result_file.split(".")[0].split("Part")[-1])
        layer = int(result_file.split(".")[-2].split("Layer")[-1])
        var_dict = {"G":
                        {"name":"Gradient",
                        "unit":"K/m"},
                    "V": 
                        {"name":"Velocity",
                        "unit":"m/s"}
                    }
        for var in var_dict:
            peregrine.upload_results(buildpath=buildpath,
                                     partnumber=part,
                                     layernumber=layer,
                                     result_file=result_file,
                                     var=var,
                                     var_name=var_dict[var]["name"],
                                     var_unit=var_dict[var]["unit"],
                                     datapath=os.path.join(
                                        "registered",
                                        var_dict[var]["name"]
                                     )
                                    )

    return 1
'''
