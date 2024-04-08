
# Importing Australian Schools

Download a JSON file of all schools in Australia
```
https://asl.acara.edu.au/School-Search
```

Each entry looks something like this:

```json
{
    "RefId": "9ac835bf8767402c900f8b93b5ef6b1a",
    "LocalId": "48096",
    "StateProvinceId": "000005817",
    "CommonwealthId": "53495",
    "ACARAId": "48096",
    "SchoolName": "A B Paterson College",
    "SchoolDistrict": "",
    "SchoolType": "Pri/Sec",
    "SchoolURL": "https://www.abpat.qld.edu.au/",
    "OperationalStatus": "O",
    "Campus": {
      "ParentSchoolId": "48096",
      "SchoolCampusId": "48096",
      "CampusType": "Pri/Sec"
    },
    "SchoolSector": "NG",
    "IndependentSchool": "Y",
    "SchoolGeographicLocation": "30",
    "LocalGovernmentArea": "",
    "AddressList": [
      {
        "Type": "0765",
        "Role": "012A",
        "City": "Arundel",
        "StateProvince": "QLD",
        "PostalCode": "4214",
        "GridLocation": {
          "Latitude": -27.927700000000000,
          "Longitude": 153.360000000000000
        },
        "Country": "1101",
        "StatisticalAreas": []
      }
    ],
    "SessionType": "0827"
  }
```

I've put the data in `s3://wriveted-data-ingestion/ingestion/aus/aus-schools.json`

