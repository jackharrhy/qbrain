from importlib.resources import files

SQL = files("qbrain").joinpath("schema.sql").read_text()
