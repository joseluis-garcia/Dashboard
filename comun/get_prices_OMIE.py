#from OMIEData.DataImport.omie_marginalprice_importer import OMIEMarginalPriceFileImporter
from OMIEData.DataImport.omie_day_ahead_importer import OMIEDayAheadPriceFileImporter

import datetime as dt

start = dt.date(2026, 1, 28)
end = dt.date(2026, 1, 28)

importer = OMIEMarginalPriceFileImporter(start, end)
print(dir(importer))
df = importer.read_to_dataframe()
print (df)