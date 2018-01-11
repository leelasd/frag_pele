# General imports
import argparse
import string
import os
import logging
# Local imports
import template_selector
import template_fragmenter_2
import simulations_linker

# Logging constants
LOG_FILENAME = "output.out"
LOG_FORMAT = "%(asctime)s:%(name)s:%(levelname)s:%(message)s"
STREAM_FORMAT = "%(asctime)s:%(message)s"
TEMPLATE_MESSAGE = "We are going to transform the template _{}_ into _{}_ in _{}_ steps! Starting..."
SELECTED_MESSAGE = "\n============ Files selected ============\nControl file: {}\nPDB file: {}\nResults folder name: {}\n"
FINISH_SIM_MESSAGE = "SIMULATION FOR control_file_grw_{} COMPLETED!!! "
# Errors messages
SELECT_ERROR_FNOTFOUND = "{}_{}/trajectory.pdb was not found. Probably the simulation did not finish properly"
SELECT_ERROR_EXCEPT = """Sorry, something went wrong when selecting a PDB from results. First, check if the criteria 
coincide with the report file column name"""
CHLG_ERROR_FNOTFOUND = "{}_{}_tmp.pdb was not found"
CHLG_ERROR_EXCEPT = "Sorry, something went wrong when changing ligand name of the selected PDB"
# Logging definition block
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

log_formatter = logging.Formatter(LOG_FORMAT)
stream_formatter = logging.Formatter(STREAM_FORMAT)

file_handler = logging.FileHandler(LOG_FILENAME)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.NOTSET)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def parse_arguments():
    """
        Parse user arguments

        Output: list with all the user arguments
    """
    parser = argparse.ArgumentParser(description="""From an input file, correspondent to the template of the initial 
    structure of the ligand,this function will generate "x_fragments" intermediate templates until reach the final 
    template,modifying Vann Der Waals, bond lengths and deleting charges.""")

    required_named = parser.add_argument_group('required named arguments')  # We have to do this in order
    # to print properly the required arguments when using the defined arguments method

    # Required arguments
    required_named.add_argument("-i", "--initial", required=True,
                                help="""input file correspondent to the 
                                initial template for the ligand that you 
                                want to grow.""")
    required_named.add_argument("-t", "--trans", required=True,
                                help="""When an atom is transformed into another
                                one we want to conserve the properties
                                of the first one until being changed in the 
                                last template. The atom name of the initial template
                                that we want to transform into another of the final
                                template has to be specified in 
                                a text file separated by whitespaces.""")
    required_named.add_argument("-c", "--contrl", required=True,
                                help='Initial control file.')
    required_named.add_argument("-p", "--pdb", required=True,
                                help="""Initial pdb file which already contain the ligand with 
                                the fragment that we want to grow but with bond lengths correspondent 
                                to the initial ligand (dummy-like).""")

    # In the future we will remove this argument
    required_named.add_argument("-f", "--final", required=True,
                                help="""Input file correspondent to the
                                final template for the ligand that you 
                                want to get.""")

    # Optional arguments
    parser.add_argument("-x", "--frag", type=int, default=10,
                        help="""Number of intermediate templates that you want 
                             to generate""")
    parser.add_argument("-r", "--resfold", default="growing_output",
                        help="Name for results folder")
    parser.add_argument("-cr", "--criteria", default="Binding Energy",
                        help="""Name of the column used as criteria in order
                             to select the template used as input for 
                             successive simulations.""")
    args = parser.parse_args()

    return args.initial, args.final, args.frag, args.trans, args.contrl, args.pdb, args.resfold, args.criteria


def main(template_initial, template_final, n_files, transformation, control_file, pdb, results_f_name, criteria):
    """
        Description: This function is the main core of the program. It creates N intermediate templates
        and control files for PELE. Then, it perform N successive simulations automatically.

        Input:

        "template_initial" --> Name of the input file correspondent to the initial template for the ligand that you
                               want to grow.

        "template_final" --> Name of the input file correspondent to the final template for the ligand that you want
                             to get.

        "n_files" --> Number of intermediate templates that you want to generate

        "transformation" --> When an atom is transformed into another one we want to conserve the properties.
                             The atom name of the initial template that we want to transform into another of
                             the final template has to be specified in a text file separated by whitespaces.

        "control_file" --> Initial control file used as template to generate intermediates control files.

        "pdb" --> Initial pdb file which already contain the ligand with the fragment that we want to grow
                  but with bond lengths correspondent to the initial ligand (dummy-like).

        "results_f_name" --> Name for results folder

        "criteria" --> Name of the column of the report file used as criteria in order to select the template
                       used as input for successive simulations.

        Output:

        First, intermediate control files and templates. Then, the results for each simulation and a pdb file for
        each selected trajectory (the last selected trajectory is the final structure with the ligand grown).

        """

    # Creating template files
    logger.info((TEMPLATE_MESSAGE.format(template_initial, template_final, n_files)))
    templates = template_fragmenter_2.fragmenter(template_initial, template_final, transformation, n_files)
    # Creating control files
    logger.info(SELECTED_MESSAGE.format(control_file, pdb, results_f_name))
    control_files = simulations_linker.control_file_modifier(control_file, pdb, results_f_name, n_files)

    # Run Pele for each control file

    # for template, control_file in zip(templates, control_files):
    for n in range(0, n_files):
        # Run Pele
        if not os.path.exists("{}_{}".format(results_f_name, string.ascii_lowercase[n])):
            os.mkdir("{}_{}".format(results_f_name, string.ascii_lowercase[n]))
            simulations_linker.simulation_runner("control_file_grw_{}".format(string.ascii_lowercase[n]))
            logger.info(FINISH_SIM_MESSAGE.format(string.ascii_lowercase[n]))
        else:
            simulations_linker.simulation_runner("control_file_grw_{}".format(string.ascii_lowercase[n]))
            logger.info(FINISH_SIM_MESSAGE.format(string.ascii_lowercase[n]))
        # Choose the best trajectory
        try:
            template_selector.trajectory_selector("{}_{}".format(results_f_name, string.ascii_lowercase[n]),
                                              "{}_{}_tmp.pdb".format(pdb, string.ascii_lowercase[n + 1]),
                                              "{}".format(criteria))
        except FileNotFoundError:
            logger.exception(SELECT_ERROR_FNOTFOUND.format(results_f_name, string.ascii_lowercase[n]))
        except Exception:
            logger.exception(SELECT_ERROR_EXCEPT)
        try:
            template_selector.change_ligandname("{}_{}_tmp.pdb".format(pdb, string.ascii_lowercase[n + 1]),
                                            "{}_{}.pdb".format(pdb, string.ascii_lowercase[n + 1]))
        except FileNotFoundError:
            logger.exception(CHLG_ERROR_FNOTFOUND.format(pdb, string.ascii_lowercase[n + 1]))
        except Exception:
            logger.exception()
        if not os.path.isfile("{}_{}.pdb".format(pdb, string.ascii_lowercase[n + 1])):
            logger.critical("We could not create {}_{}.pdb".format(pdb, string.ascii_lowercase[n + 1]))
            exit()
        else:
            logger.info("Step of the Trajectory selected in {}_{}.pdb".format(pdb, string.ascii_lowercase[n + 1]))


if __name__ == '__main__':
    init, final, frag, trans, control, pdb, res_fold, criteria = parse_arguments()
    main(init, final, frag, trans, control, pdb, res_fold, criteria)
