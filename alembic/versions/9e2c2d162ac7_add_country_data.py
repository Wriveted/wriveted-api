"""Add country data

Revision ID: 9e2c2d162ac7
Revises: a65ff088f9ae
Create Date: 2021-12-27 10:16:36.191379

"""

# revision identifiers, used by Alembic.
from sqlalchemy import orm

from alembic import op
from app.models import Country

revision = "9e2c2d162ac7"
down_revision = "a65ff088f9ae"
branch_labels = None
depends_on = None

country_data = [
    {"iso3": "AFG", "nicename": "Afghanistan", "phonecode": 93},
    {"iso3": "ALB", "nicename": "Albania", "phonecode": 355},
    {"iso3": "DZA", "nicename": "Algeria", "phonecode": 213},
    {"iso3": "ASM", "nicename": "American Samoa", "phonecode": 1684},
    {"iso3": "AND", "nicename": "Andorra", "phonecode": 376},
    {"iso3": "AGO", "nicename": "Angola", "phonecode": 244},
    {"iso3": "AIA", "nicename": "Anguilla", "phonecode": 1264},
    {"iso3": "ATA", "nicename": "Antarctica", "phonecode": 0},
    {"iso3": "ATG", "nicename": "Antigua and Barbuda", "phonecode": 1268},
    {"iso3": "ARG", "nicename": "Argentina", "phonecode": 54},
    {"iso3": "ARM", "nicename": "Armenia", "phonecode": 374},
    {"iso3": "ABW", "nicename": "Aruba", "phonecode": 297},
    {"iso3": "AUS", "nicename": "Australia", "phonecode": 61},
    {"iso3": "AUT", "nicename": "Austria", "phonecode": 43},
    {"iso3": "AZE", "nicename": "Azerbaijan", "phonecode": 994},
    {"iso3": "BHS", "nicename": "Bahamas", "phonecode": 1242},
    {"iso3": "BHR", "nicename": "Bahrain", "phonecode": 973},
    {"iso3": "BGD", "nicename": "Bangladesh", "phonecode": 880},
    {"iso3": "BRB", "nicename": "Barbados", "phonecode": 1246},
    {"iso3": "BLR", "nicename": "Belarus", "phonecode": 375},
    {"iso3": "BEL", "nicename": "Belgium", "phonecode": 32},
    {"iso3": "BLZ", "nicename": "Belize", "phonecode": 501},
    {"iso3": "BEN", "nicename": "Benin", "phonecode": 229},
    {"iso3": "BMU", "nicename": "Bermuda", "phonecode": 1441},
    {"iso3": "BTN", "nicename": "Bhutan", "phonecode": 975},
    {"iso3": "BOL", "nicename": "Bolivia", "phonecode": 591},
    {"iso3": "BIH", "nicename": "Bosnia and Herzegovina", "phonecode": 387},
    {"iso3": "BWA", "nicename": "Botswana", "phonecode": 267},
    {"iso3": "BVT", "nicename": "Bouvet Island", "phonecode": 0},
    {"iso3": "BRA", "nicename": "Brazil", "phonecode": 55},
    {"iso3": "IOT", "nicename": "British Indian Ocean Territory", "phonecode": 246},
    {"iso3": "BRN", "nicename": "Brunei Darussalam", "phonecode": 673},
    {"iso3": "BGR", "nicename": "Bulgaria", "phonecode": 359},
    {"iso3": "BFA", "nicename": "Burkina Faso", "phonecode": 226},
    {"iso3": "BDI", "nicename": "Burundi", "phonecode": 257},
    {"iso3": "KHM", "nicename": "Cambodia", "phonecode": 855},
    {"iso3": "CMR", "nicename": "Cameroon", "phonecode": 237},
    {"iso3": "CAN", "nicename": "Canada", "phonecode": 1},
    {"iso3": "CPV", "nicename": "Cape Verde", "phonecode": 238},
    {"iso3": "CYM", "nicename": "Cayman Islands", "phonecode": 1345},
    {"iso3": "CAF", "nicename": "Central African Republic", "phonecode": 236},
    {"iso3": "TCD", "nicename": "Chad", "phonecode": 235},
    {"iso3": "CHL", "nicename": "Chile", "phonecode": 56},
    {"iso3": "CHN", "nicename": "China", "phonecode": 86},
    {"iso3": "CXR", "nicename": "Christmas Island", "phonecode": 61},
    {"iso3": "COL", "nicename": "Colombia", "phonecode": 57},
    {"iso3": "COM", "nicename": "Comoros", "phonecode": 269},
    {"iso3": "COG", "nicename": "Congo", "phonecode": 242},
    {
        "iso3": "COD",
        "nicename": "Congo, the Democratic Republic of the",
        "phonecode": 242,
    },
    {"iso3": "COK", "nicename": "Cook Islands", "phonecode": 682},
    {"iso3": "CRI", "nicename": "Costa Rica", "phonecode": 506},
    {"iso3": "CIV", "nicename": "Cote D'Ivoire", "phonecode": 225},
    {"iso3": "HRV", "nicename": "Croatia", "phonecode": 385},
    {"iso3": "CUB", "nicename": "Cuba", "phonecode": 53},
    {"iso3": "CYP", "nicename": "Cyprus", "phonecode": 357},
    {"iso3": "CZE", "nicename": "Czech Republic", "phonecode": 420},
    {"iso3": "DNK", "nicename": "Denmark", "phonecode": 45},
    {"iso3": "DJI", "nicename": "Djibouti", "phonecode": 253},
    {"iso3": "DMA", "nicename": "Dominica", "phonecode": 1767},
    {"iso3": "DOM", "nicename": "Dominican Republic", "phonecode": 1},
    {"iso3": "ECU", "nicename": "Ecuador", "phonecode": 593},
    {"iso3": "EGY", "nicename": "Egypt", "phonecode": 20},
    {"iso3": "SLV", "nicename": "El Salvador", "phonecode": 503},
    {"iso3": "GNQ", "nicename": "Equatorial Guinea", "phonecode": 240},
    {"iso3": "ERI", "nicename": "Eritrea", "phonecode": 291},
    {"iso3": "EST", "nicename": "Estonia", "phonecode": 372},
    {"iso3": "ETH", "nicename": "Ethiopia", "phonecode": 251},
    {"iso3": "FLK", "nicename": "Falkland Islands (Malvinas)", "phonecode": 500},
    {"iso3": "FRO", "nicename": "Faroe Islands", "phonecode": 298},
    {"iso3": "FJI", "nicename": "Fiji", "phonecode": 679},
    {"iso3": "FIN", "nicename": "Finland", "phonecode": 358},
    {"iso3": "FRA", "nicename": "France", "phonecode": 33},
    {"iso3": "GUF", "nicename": "French Guiana", "phonecode": 594},
    {"iso3": "PYF", "nicename": "French Polynesia", "phonecode": 689},
    {"iso3": "ATF", "nicename": "French Southern Territories", "phonecode": 0},
    {"iso3": "GAB", "nicename": "Gabon", "phonecode": 241},
    {"iso3": "GMB", "nicename": "Gambia", "phonecode": 220},
    {"iso3": "GEO", "nicename": "Georgia", "phonecode": 995},
    {"iso3": "DEU", "nicename": "Germany", "phonecode": 49},
    {"iso3": "GHA", "nicename": "Ghana", "phonecode": 233},
    {"iso3": "GIB", "nicename": "Gibraltar", "phonecode": 350},
    {"iso3": "GRC", "nicename": "Greece", "phonecode": 30},
    {"iso3": "GRL", "nicename": "Greenland", "phonecode": 299},
    {"iso3": "GRD", "nicename": "Grenada", "phonecode": 1473},
    {"iso3": "GLP", "nicename": "Guadeloupe", "phonecode": 590},
    {"iso3": "GUM", "nicename": "Guam", "phonecode": 1671},
    {"iso3": "GTM", "nicename": "Guatemala", "phonecode": 502},
    {"iso3": "GIN", "nicename": "Guinea", "phonecode": 224},
    {"iso3": "GNB", "nicename": "Guinea-Bissau", "phonecode": 245},
    {"iso3": "GUY", "nicename": "Guyana", "phonecode": 592},
    {"iso3": "HTI", "nicename": "Haiti", "phonecode": 509},
    {"iso3": "HMD", "nicename": "Heard Island and Mcdonald Islands", "phonecode": 0},
    {"iso3": "VAT", "nicename": "Holy See (Vatican City State)", "phonecode": 39},
    {"iso3": "HND", "nicename": "Honduras", "phonecode": 504},
    {"iso3": "HKG", "nicename": "Hong Kong", "phonecode": 852},
    {"iso3": "HUN", "nicename": "Hungary", "phonecode": 36},
    {"iso3": "ISL", "nicename": "Iceland", "phonecode": 354},
    {"iso3": "IND", "nicename": "India", "phonecode": 91},
    {"iso3": "IDN", "nicename": "Indonesia", "phonecode": 62},
    {"iso3": "IRN", "nicename": "Iran, Islamic Republic of", "phonecode": 98},
    {"iso3": "IRQ", "nicename": "Iraq", "phonecode": 964},
    {"iso3": "IRL", "nicename": "Ireland", "phonecode": 353},
    {"iso3": "ISR", "nicename": "Israel", "phonecode": 972},
    {"iso3": "ITA", "nicename": "Italy", "phonecode": 39},
    {"iso3": "JAM", "nicename": "Jamaica", "phonecode": 1876},
    {"iso3": "JPN", "nicename": "Japan", "phonecode": 81},
    {"iso3": "JOR", "nicename": "Jordan", "phonecode": 962},
    {"iso3": "KAZ", "nicename": "Kazakhstan", "phonecode": 7},
    {"iso3": "KEN", "nicename": "Kenya", "phonecode": 254},
    {"iso3": "KIR", "nicename": "Kiribati", "phonecode": 686},
    {
        "iso3": "PRK",
        "nicename": "Korea, Democratic People's Republic of",
        "phonecode": 850,
    },
    {"iso3": "KOR", "nicename": "Korea, Republic of", "phonecode": 82},
    {"iso3": "KWT", "nicename": "Kuwait", "phonecode": 965},
    {"iso3": "KGZ", "nicename": "Kyrgyzstan", "phonecode": 996},
    {"iso3": "LAO", "nicename": "Lao People's Democratic Republic", "phonecode": 856},
    {"iso3": "LVA", "nicename": "Latvia", "phonecode": 371},
    {"iso3": "LBN", "nicename": "Lebanon", "phonecode": 961},
    {"iso3": "LSO", "nicename": "Lesotho", "phonecode": 266},
    {"iso3": "LBR", "nicename": "Liberia", "phonecode": 231},
    {"iso3": "LBY", "nicename": "Libyan Arab Jamahiriya", "phonecode": 218},
    {"iso3": "LIE", "nicename": "Liechtenstein", "phonecode": 423},
    {"iso3": "LTU", "nicename": "Lithuania", "phonecode": 370},
    {"iso3": "LUX", "nicename": "Luxembourg", "phonecode": 352},
    {"iso3": "MAC", "nicename": "Macao", "phonecode": 853},
    {"iso3": "MKD", "nicename": "North Macedonia", "phonecode": 389},
    {"iso3": "MDG", "nicename": "Madagascar", "phonecode": 261},
    {"iso3": "MWI", "nicename": "Malawi", "phonecode": 265},
    {"iso3": "MYS", "nicename": "Malaysia", "phonecode": 60},
    {"iso3": "MDV", "nicename": "Maldives", "phonecode": 960},
    {"iso3": "MLI", "nicename": "Mali", "phonecode": 223},
    {"iso3": "MLT", "nicename": "Malta", "phonecode": 356},
    {"iso3": "MHL", "nicename": "Marshall Islands", "phonecode": 692},
    {"iso3": "MTQ", "nicename": "Martinique", "phonecode": 596},
    {"iso3": "MRT", "nicename": "Mauritania", "phonecode": 222},
    {"iso3": "MUS", "nicename": "Mauritius", "phonecode": 230},
    {"iso3": "MYT", "nicename": "Mayotte", "phonecode": 269},
    {"iso3": "MEX", "nicename": "Mexico", "phonecode": 52},
    {"iso3": "FSM", "nicename": "Micronesia, Federated States of", "phonecode": 691},
    {"iso3": "MDA", "nicename": "Moldova, Republic of", "phonecode": 373},
    {"iso3": "MCO", "nicename": "Monaco", "phonecode": 377},
    {"iso3": "MNG", "nicename": "Mongolia", "phonecode": 976},
    {"iso3": "MSR", "nicename": "Montserrat", "phonecode": 1664},
    {"iso3": "MAR", "nicename": "Morocco", "phonecode": 212},
    {"iso3": "MOZ", "nicename": "Mozambique", "phonecode": 258},
    {"iso3": "MMR", "nicename": "Myanmar", "phonecode": 95},
    {"iso3": "NAM", "nicename": "Namibia", "phonecode": 264},
    {"iso3": "NRU", "nicename": "Nauru", "phonecode": 674},
    {"iso3": "NPL", "nicename": "Nepal", "phonecode": 977},
    {"iso3": "NLD", "nicename": "Netherlands", "phonecode": 31},
    {"iso3": "ANT", "nicename": "Netherlands Antilles", "phonecode": 599},
    {"iso3": "NCL", "nicename": "New Caledonia", "phonecode": 687},
    {"iso3": "NZL", "nicename": "New Zealand", "phonecode": 64},
    {"iso3": "NIC", "nicename": "Nicaragua", "phonecode": 505},
    {"iso3": "NER", "nicename": "Niger", "phonecode": 227},
    {"iso3": "NGA", "nicename": "Nigeria", "phonecode": 234},
    {"iso3": "NIU", "nicename": "Niue", "phonecode": 683},
    {"iso3": "NFK", "nicename": "Norfolk Island", "phonecode": 672},
    {"iso3": "MNP", "nicename": "Northern Mariana Islands", "phonecode": 1670},
    {"iso3": "NOR", "nicename": "Norway", "phonecode": 47},
    {"iso3": "OMN", "nicename": "Oman", "phonecode": 968},
    {"iso3": "PAK", "nicename": "Pakistan", "phonecode": 92},
    {"iso3": "PLW", "nicename": "Palau", "phonecode": 680},
    {"iso3": "PAN", "nicename": "Panama", "phonecode": 507},
    {"iso3": "PNG", "nicename": "Papua New Guinea", "phonecode": 675},
    {"iso3": "PRY", "nicename": "Paraguay", "phonecode": 595},
    {"iso3": "PER", "nicename": "Peru", "phonecode": 51},
    {"iso3": "PHL", "nicename": "Philippines", "phonecode": 63},
    {"iso3": "PCN", "nicename": "Pitcairn", "phonecode": 0},
    {"iso3": "POL", "nicename": "Poland", "phonecode": 48},
    {"iso3": "PRT", "nicename": "Portugal", "phonecode": 351},
    {"iso3": "PRI", "nicename": "Puerto Rico", "phonecode": 1787},
    {"iso3": "QAT", "nicename": "Qatar", "phonecode": 974},
    {"iso3": "REU", "nicename": "Reunion", "phonecode": 262},
    {"iso3": "ROU", "nicename": "Romania", "phonecode": 40},
    {"iso3": "RUS", "nicename": "Russian Federation", "phonecode": 7},
    {"iso3": "RWA", "nicename": "Rwanda", "phonecode": 250},
    {"iso3": "SHN", "nicename": "Saint Helena", "phonecode": 290},
    {"iso3": "KNA", "nicename": "Saint Kitts and Nevis", "phonecode": 1869},
    {"iso3": "LCA", "nicename": "Saint Lucia", "phonecode": 1758},
    {"iso3": "SPM", "nicename": "Saint Pierre and Miquelon", "phonecode": 508},
    {"iso3": "VCT", "nicename": "Saint Vincent and the Grenadines", "phonecode": 1784},
    {"iso3": "WSM", "nicename": "Samoa", "phonecode": 684},
    {"iso3": "SMR", "nicename": "San Marino", "phonecode": 378},
    {"iso3": "STP", "nicename": "Sao Tome and Principe", "phonecode": 239},
    {"iso3": "SAU", "nicename": "Saudi Arabia", "phonecode": 966},
    {"iso3": "SEN", "nicename": "Senegal", "phonecode": 221},
    {"iso3": "SRB", "nicename": "Serbia", "phonecode": 381},
    {"iso3": "SYC", "nicename": "Seychelles", "phonecode": 248},
    {"iso3": "SLE", "nicename": "Sierra Leone", "phonecode": 232},
    {"iso3": "SGP", "nicename": "Singapore", "phonecode": 65},
    {"iso3": "SVK", "nicename": "Slovakia", "phonecode": 421},
    {"iso3": "SVN", "nicename": "Slovenia", "phonecode": 386},
    {"iso3": "SLB", "nicename": "Solomon Islands", "phonecode": 677},
    {"iso3": "SOM", "nicename": "Somalia", "phonecode": 252},
    {"iso3": "ZAF", "nicename": "South Africa", "phonecode": 27},
    {
        "iso3": "SGS",
        "nicename": "South Georgia and the South Sandwich Islands",
        "phonecode": 0,
    },
    {"iso3": "ESP", "nicename": "Spain", "phonecode": 34},
    {"iso3": "LKA", "nicename": "Sri Lanka", "phonecode": 94},
    {"iso3": "SDN", "nicename": "Sudan", "phonecode": 249},
    {"iso3": "SUR", "nicename": "Suriname", "phonecode": 597},
    {"iso3": "SJM", "nicename": "Svalbard and Jan Mayen", "phonecode": 47},
    {"iso3": "SWZ", "nicename": "Swaziland", "phonecode": 268},
    {"iso3": "SWE", "nicename": "Sweden", "phonecode": 46},
    {"iso3": "CHE", "nicename": "Switzerland", "phonecode": 41},
    {"iso3": "SYR", "nicename": "Syrian Arab Republic", "phonecode": 963},
    {"iso3": "TWN", "nicename": "Taiwan, Province of China", "phonecode": 886},
    {"iso3": "TJK", "nicename": "Tajikistan", "phonecode": 992},
    {"iso3": "TZA", "nicename": "Tanzania, United Republic of", "phonecode": 255},
    {"iso3": "THA", "nicename": "Thailand", "phonecode": 66},
    {"iso3": "TLS", "nicename": "Timor-Leste", "phonecode": 670},
    {"iso3": "TGO", "nicename": "Togo", "phonecode": 228},
    {"iso3": "TKL", "nicename": "Tokelau", "phonecode": 690},
    {"iso3": "TON", "nicename": "Tonga", "phonecode": 676},
    {"iso3": "TTO", "nicename": "Trinidad and Tobago", "phonecode": 1868},
    {"iso3": "TUN", "nicename": "Tunisia", "phonecode": 216},
    {"iso3": "TUR", "nicename": "Turkey", "phonecode": 90},
    {"iso3": "TKM", "nicename": "Turkmenistan", "phonecode": 993},
    {"iso3": "TCA", "nicename": "Turks and Caicos Islands", "phonecode": 1649},
    {"iso3": "TUV", "nicename": "Tuvalu", "phonecode": 688},
    {"iso3": "UGA", "nicename": "Uganda", "phonecode": 256},
    {"iso3": "UKR", "nicename": "Ukraine", "phonecode": 380},
    {"iso3": "ARE", "nicename": "United Arab Emirates", "phonecode": 971},
    {"iso3": "GBR", "nicename": "United Kingdom", "phonecode": 44},
    {"iso3": "USA", "nicename": "United States", "phonecode": 1},
    {"iso3": "UMI", "nicename": "United States Minor Outlying Islands", "phonecode": 1},
    {"iso3": "URY", "nicename": "Uruguay", "phonecode": 598},
    {"iso3": "UZB", "nicename": "Uzbekistan", "phonecode": 998},
    {"iso3": "VUT", "nicename": "Vanuatu", "phonecode": 678},
    {"iso3": "VEN", "nicename": "Venezuela", "phonecode": 58},
    {"iso3": "VNM", "nicename": "Viet Nam", "phonecode": 84},
    {"iso3": "VGB", "nicename": "Virgin Islands, British", "phonecode": 1284},
    {"iso3": "VIR", "nicename": "Virgin Islands, U.s.", "phonecode": 1340},
    {"iso3": "WLF", "nicename": "Wallis and Futuna", "phonecode": 681},
    {"iso3": "ESH", "nicename": "Western Sahara", "phonecode": 212},
    {"iso3": "YEM", "nicename": "Yemen", "phonecode": 967},
    {"iso3": "ZMB", "nicename": "Zambia", "phonecode": 260},
    {"iso3": "ZWE", "nicename": "Zimbabwe", "phonecode": 263},
    {"iso3": "MNE", "nicename": "Montenegro", "phonecode": 382},
    {"iso3": "XKX", "nicename": "Kosovo", "phonecode": 383},
    {"iso3": "ALA", "nicename": "Aland Islands", "phonecode": 358},
    {"iso3": "BES", "nicename": "Bonaire, Sint Eustatius and Saba", "phonecode": 599},
    {"iso3": "CUW", "nicename": "Curacao", "phonecode": 599},
    {"iso3": "GGY", "nicename": "Guernsey", "phonecode": 44},
    {"iso3": "IMN", "nicename": "Isle of Man", "phonecode": 44},
    {"iso3": "JEY", "nicename": "Jersey", "phonecode": 44},
    {"iso3": "BLM", "nicename": "Saint Barthelemy", "phonecode": 590},
    {"iso3": "MAF", "nicename": "Saint Martin", "phonecode": 590},
    {"iso3": "SXM", "nicename": "Sint Maarten", "phonecode": 1},
    {"iso3": "SSD", "nicename": "South Sudan", "phonecode": 211},
]


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for data in country_data:
        session.add(
            Country(id=data["iso3"], name=data["nicename"], phonecode=data["phonecode"])
        )
    session.commit()

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    session.query(Country).delete()
    # ### end Alembic commands ###
