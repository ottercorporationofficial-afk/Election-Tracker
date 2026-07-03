from api import get_race
import storage


RACE_ID = 84287

data = get_race(RACE_ID)

print(data["election_name"])

storage.save_snapshot(data)