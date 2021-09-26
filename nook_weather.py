import flask
import urllib3
import json
import datetime
import os

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

    time_threshold = datetime.timedelta(hours=2)

    new_reps = []
    for idx in range(0, len(reps)):
        r = reps[idx]

        # Time in mins
        mins = r["$"]
        r["mins"] = mins

        # 12-hr time
        d = datetime.datetime.now()
        d = d.replace(hour=(int(int(mins)/60)), minute=0, second=0, microsecond=0)
        r["time"] = d.strftime("%H%M")

        if datetime.datetime.now() - time_threshold > d:
            continue

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

        # Append new rep
        new_reps.append(r)

    return (date, new_reps)


def build_wx_data(location):
    if not location in LOC_MAP:
        raise Exception(f"Unknown location {location}")

    loc_id = LOC_MAP[location]
    wx = get_wx(loc_id)

    if wx is None:
        raise Exception("Error retrieving wx")

    return process_wx(wx)


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
            return flask.url_for(endpoint, **values)

@app.route('/', methods=['GET'])
def home():
    return "<h1>Nook MetOffice Weather</h1><p>Available endpoints:</p><ul><li>/weather</li></ul>"


@app.route('/weather', methods=['GET'])
def wxfcs():
    try:
        page_data = build_wx_data("sale")
    except Exception as e:
        return f"Error: {e}."

    return flask.render_template("wxfcs.html", period_limit=3, date=page_data[0], wx_periods=page_data[1])


if __name__ == "__main__":
    app.run(host='0.0.0.0')
