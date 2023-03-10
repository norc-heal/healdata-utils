''' 

command line interface for generating HEAL data dictionary/vlmd json files

#TODO: make scheam a CLI option?
#TODO: port to_json and to_csv fxns outputside of CLI? to an io.py folder?
''' 


import click 
from healdata_utils.transforms.csvtemplate.conversion import convert_templatecsv
from healdata_utils.transforms.jsontemplate.conversion import convert_templatejson
from healdata_utils.transforms.readstat.conversion import convert_readstat
from healdata_utils.transforms.redcapcsv.conversion import convert_redcapcsv
import json
from pathlib import Path
from healdata_utils.schemas import validate_json,validate_csv
import pandas as pd
import petl as etl
from collections import deque

from healdata_utils.utils import find_docstring_desc

choice_fxn = {
    'csv': convert_templatecsv,
    'sav': convert_readstat,
    'dta':convert_readstat,
    'por':convert_readstat,
    'sas7bdat':convert_readstat,
    'json':convert_templatejson,
    "redcap.csv":convert_redcapcsv

}

input_types = " - "+"\n - ".join(list(choice_fxn.keys()))

input_descriptions = {
    name:find_docstring_desc(fxn)
    for name,fxn in choice_fxn.items()
}

def convert_to_vlmd(
    filepath,
    data_dictionary_props={},
    inputtype=None,
    outputdir=None,

    ):
    """
    Writes a data dictionary (i.e. variable level metadata) to a HEAL metadata JSON file using a registered function.

    Parameters
    ----------
    filepath : str
        Path to input file. See documentation on individual input types for more details.
    outputdir : str
        Path to a directory where output will go. If a directory is specified, will use the input name for output name replaced with JSON suffix.
    data_dictionary_props : dict, optional
        The other data-dictionary level properties. By default, will give the data_dictionary `title` property as the file name stem.
    inputtype : str, optional
        The input type. If none specified, will default to using the file extension.
        See the currently registered input types in the input_types list.
    save_path : str, optional
        Path to output directory. Default is to not save.

    Returns
    -------
    dict
        Dictionary with:
         1. csvtemplated array of fields.
         2. jsontemplated data dictionary object as specified by an originally drafted design doc.
            That is, a dictionary with title:<title>,description:<description>,data_dictionary:<fields>
            where data dictionary is an array of fields as specified by the JSON schema.
         3. error objects for corresponding validators (ie frictionless for csv and jsonschema for json)
    NOTE
    ----
    In future versions, this will be more of a package bundled with corresponding schemas (whether csv or JSON),better organization 
    (e.g., see frictionless Package). 
    However, right now, it simply returns the csvtemplate and jsontemplate as specified
    in the heal specification repository.
    This is an intermediate solution to socialize a proof-of-concept.
    
    """

    filepath = Path(filepath)
    outputdir = Path(outputdir)
    #infer input type
    if not inputtype:
        inputtype = ''.join(filepath.suffixes)[1:].lower()

    ## add dd title
    if not data_dictionary_props.get('title'):
        data_dictionary_props['title'] = filepath.stem

    # get data dictionary package based on the input type
    data_dictionary_package = choice_fxn[inputtype](filepath,data_dictionary_props)

    fields_csv,report_csv = validate_csv(
        data_dictionary_package['templatecsv']['data_dictionary']
    )
    fields_json,report_json = validate_json(
        data_dictionary_package['templatejson']
    )

    # write to file
    if outputdir!=None:
        if Path(outputdir).is_dir():
            jsontemplate_path = outputdir/"heal-jsontemplate-data-dictionary.json"
            csvtemplate_path = outputdir/"heal-csvtemplate-data-dictionary.csv"
        else:
            raise Exception("outputdir must be an existing directory where files can be saved")
        
        # print data dictionaries
        templatejson = {**data_dictionary_props,'data_dictionary':fields_json}
        jsontemplate_path.write_text(json.dumps(templatejson,indent=4))

        etl.fromdicts(fields_csv).tocsv(csvtemplate_path)

        # print errors
        items = [list(item) if type(item)==deque else item for item in report_json.values()]
        keys = list(report_json.keys())
        jsonerrors = dict(zip(keys,items))
        if not jsonerrors['valid']:
            print("JSON data dictionary not valid, see heal-json-errors.json")
 
        if not report_csv['valid']:
            print("CSV data dictionary not valid, see heal-csv-errors.json and")
            print("heal-csv-errors-summary.txt (which is a more human-readable error report)")
        
        
        # write error reports to file
        errordir = Path(outputdir).joinpath('errors')
        errordir.mkdir(exist_ok=True)
        errordir.joinpath('heal-json-errors.json').write_text(
            json.dumps(jsonerrors,indent=4)
        )
        report_csv.to_json(errordir/"heal-csv-errors.json")
        errordir.joinpath("heal-csv-errors-summary.txt").write_text(
            report_csv.to_summary()
        )
    
    return {
        "csvtemplate":fields_csv,
        "jsontemplate":templatejson,
        "errors":{
            "csvtemplate":report_csv,
            "jsontemplate":report_json}
        }

@click.command()
@click.option('--filepath',required=True,help='Path to the file you want to convert to a HEAL data dictionary')
@click.option('--title',default=None,help='The title of your data dictionary. If not specified, then the file name will be used')
@click.option('--description',default=None,help='Description of data dictionary')
@click.option('--inputtype',default=None,type=click.Choice(list(choice_fxn.keys())),help='The type of your input file.')
@click.option('--outputdir',default="",help='The folder where you want to output your HEAL data dictionary')
def main(filepath,title,description,inputtype,outputdir):
    data_dictionary_props = {'title':title,'description':description}

    #save dds and error reports to files
    data_dictionaries = convert_to_vlmd(
        filepath=filepath,
        data_dictionary_props=data_dictionary_props,
        outputdir=outputdir,
        inputtype=inputtype,

    )
     
if __name__=='__main__':
    main()