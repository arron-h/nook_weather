import flask
import urllib3
import json
import datetime

app = flask.Flask(__name__)

API_KEY = "6fab15c1-0415-4df5-b4d9-52f3ac6dc7c3"

LOC_MAP = {
    "sale": "353337"
}

WX_STR_MAP = {
    0: "Clear night",
    1: "Sunny day",
    2: "Partly cloudy",
    3: "Partly cloudy",
    5: "Mist",
    6: "Fog",
    7: "Cloudy",
    8: "Overcast",
    9: "Light rain shower",
    10: "Light rain shower",
    11: "Drizzle",
    12: "Light rain",
    13: "Heavy rain shower",
    14: "Heavy rain shower",
    15: "Heavy rain",
    16: "Sleet shower",
    17: "Sleet shower",
    18: "Sleet",
    19: "Hail shower",
    20: "Hail shower",
    21: "Hail",
    22: "Light snow shower",
    23: "Light snow shower",
    24: "Light snow",
    25: "Heavy snow shower",
    26: "Heavy snow shower",
    27: "Heavy snow",
    28: "Thunder shower",
    29: "Thunder shower",
    30: "Thunder"
}

VIS_STR_MAP = {
    "UN": "Unknown",
    "VP": "Very poor",
    "PO": "Poor",
    "MO": "Moderate",
    "GO": "Good",
    "VG": "Very good",
    "EX": "Excellent"
}

def get_wx(location_id):
    http = urllib3.PoolManager()

    url = f'http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/{location_id}?res=3hourly&key={API_KEY}'
    r = http.request('GET', url)

    if (r.status != 200):
        return None

    try:
        decoded_data = r.data.decode("utf-8")
        json_data = json.loads(decoded_data)
    except Exception as e:
        raise RuntimeError(f"Loading JSON: {e}")
    
    return json_data


def process_wx(raw_wx):
    periods = raw_wx["SiteRep"]["DV"]["Location"]["Period"]
    this_period = periods[0]

    reps = this_period["Rep"]
    value = this_period["value"]
    d = datetime.datetime.strptime(value, "%Y-%m-%dZ")
    date = d.strftime("%A %d %B")

    for idx in range(0, len(reps)):
        r = reps[idx]

        # Time in mins
        mins = r["$"]
        r["mins"] = mins

        # 12-hr time
        d = datetime.datetime.strptime(str(int(int(mins) / 60)) + "00", "%H%M")
        r["time"] = d.strftime("%H%M")

        # UV exposure
        uv_idx = int(r["U"])
        uv_str = ""
        if uv_idx <= 2:
            uv_str = "Low"
        elif uv_idx <= 5:
            uv_str = "Moderate"
        elif uv_idx <= 7:
            uv_str = "High"
        elif uv_idx <= 10:
            uv_str = "Very High"
        else:
            uv_str = "Extreme"

        r["uv"] = uv_str

        # Weather code
        wx_code = int(r["W"])
        wx_str = WX_STR_MAP[wx_code]
        r["wx"] = wx_str

        # Visibility
        vis_code = r["V"]
        vis_str = VIS_STR_MAP[vis_code]
        r["vis"] = vis_str

        # Set rep at index
        reps[idx] = r

    return (date, reps)


def build_wx_data(location):
    if not location in LOC_MAP:
        raise Exception(f"Unknown location {location}")

    loc_id = LOC_MAP[location]
    wx = get_wx(loc_id)

    if wx is None:
        raise Exception("Error retrieving wx")

    return process_wx(wx)


@app.route('/', methods=['GET'])
def home():
    return "<h1>Nook MetOffice Weather</h1><p>Available endpoints:</p><ul><li>/wxfcs/sale</li></ul>"


@app.route('/wxfcs', methods=['GET'])
def wxfcs():
    try:
        page_data = build_wx_data("sale")
    except Exception as e:
        return f"Error: {e}."

    return flask.render_template("wxfcs.html", date=page_data[0], wx_periods=page_data[1])


if __name__ == "__main__":
    app.run(host='0.0.0.0')
