import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "bot.db"
)

ROMANIAN_COUNTIES = {
    "AB": "Alba",
    "AR": "Arad",
    "AG": "Argeș",
    "BC": "Bacău",
    "BH": "Bihor",
    "BN": "Bistrița-Năsăud",
    "BT": "Botoșani",
    "BR": "Brăila",
    "BV": "Brașov",
    "BZ": "Buzău",
    "CL": "Călărași",
    "CS": "Caraș-Severin",
    "CJ": "Cluj",
    "CT": "Constanța",
    "CV": "Covasna",
    "DB": "Dâmbovița",
    "DJ": "Dolj",
    "GL": "Galați",
    "GR": "Giurgiu",
    "GJ": "Gorj",
    "HR": "Harghita",
    "HD": "Hunedoara",
    "IL": "Ialomița",
    "IS": "Iași",
    "IF": "Ilfov",
    "MM": "Maramureș",
    "MH": "Mehedinți",
    "MS": "Mureș",
    "NT": "Neamț",
    "OT": "Olt",
    "PH": "Prahova",
    "SM": "Satu Mare",
    "SJ": "Sălaj",
    "SB": "Sibiu",
    "SV": "Suceava",
    "TR": "Teleorman",
    "TM": "Timiș",
    "TL": "Tulcea",
    "VS": "Vaslui",
    "VL": "Vâlcea",
    "VN": "Vrancea",
    "B": "București",
}

class CountyService:
    @staticmethod
    def get_player_county(
        osu_id: int,
    ) -> sqlite3.Row | None:
        if not DATABASE_PATH.exists():
            return None

        with sqlite3.connect(DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row

            return connection.execute(
                """
                SELECT
                    county_code,
                    county_name,
                    county_rank,
                    pp,
                    global_rank,
                    last_updated
                FROM osu_counties
                WHERE osu_id = ?
                """,
                (osu_id,),
            ).fetchone()