"""ReCircuit - E-Waste Decision and Pickup Planner (EVS assignment prototype)

Run:  pip install streamlit
      streamlit run app.py

All numbers are illustrative sample values. Replace them with cited figures
(e-waste studies, emission factor tables) and use a CPCB-listed recycler
before submitting.
"""
import copy
import datetime as dt

import streamlit as st

st.set_page_config(page_title="ReCircuit", page_icon="♻️", layout="wide")

# ---------------------------------------------------------------- data
PICKUP_THRESHOLD = 10  # items needed in an area before a pickup is proposed
AREAS = ["Hostel A", "Hostel B", "Hostel C", "Staff quarters"]

# kg = weight, co2 = footprint of making the device (kg CO2),
# battery = has a battery, mats = grams of material inside
DEVICES = {
    "Smartphone": dict(kg=0.18, co2=60, battery=True, mats={"Copper": 15, "Aluminium": 25, "Cobalt": 5, "Gold": 0.03}),
    "Laptop": dict(kg=2.2, co2=300, battery=True, mats={"Copper": 130, "Aluminium": 300, "Cobalt": 60, "Gold": 0.2}),
    "Tablet": dict(kg=0.5, co2=100, battery=True, mats={"Copper": 30, "Aluminium": 90, "Cobalt": 15, "Gold": 0.05}),
    "LED TV": dict(kg=8, co2=400, battery=False, mats={"Copper": 400, "Aluminium": 900, "Cobalt": 0, "Gold": 0.1}),
    "Power bank": dict(kg=0.25, co2=20, battery=True, mats={"Copper": 10, "Aluminium": 20, "Cobalt": 25, "Gold": 0}),
    "Charger and cables": dict(kg=0.15, co2=5, battery=False, mats={"Copper": 40, "Aluminium": 2, "Cobalt": 0, "Gold": 0}),
}
# share of the making-footprint saved by each route
SAVING = {"Repair": 0.6, "Resell or donate": 0.5, "Authorised recycling": 0.15, "Dump in garbage": 0.0}
RECOVERY = 0.8  # share of materials recovered by authorised recycling

WHY = {
    "Repair": "A repair keeps the device in use and avoids the footprint of making a new one.",
    "Resell or donate": "The device still works, so passing it on saves the most resources.",
    "Authorised recycling": "It cannot be reused safely, so an authorised recycler recovers the metals and handles the toxic parts.",
    "Dump in garbage": "",
}

SEED = {
    "reqs": {"Hostel A": [8, 6.0], "Hostel B": [3, 2.0], "Hostel C": [0, 0.0], "Staff quarters": [4, 5.0]},
    "tot": {"items": 15, "kg": 13.0, "co2": 60.0, "copper": 420.0},
}


# ---------------------------------------------------------------- logic
def score_routes(condition, age, damaged):
    """Rule table: higher score = better for the environment."""
    if condition == "Works fine":
        s = {"Repair": 20, "Resell or donate": 90, "Authorised recycling": 40, "Dump in garbage": 0}
    elif condition == "Partly working":
        s = {"Repair": 85, "Resell or donate": 55, "Authorised recycling": 50, "Dump in garbage": 0}
    else:  # Dead
        s = {"Repair": 60, "Resell or donate": 15, "Authorised recycling": 85, "Dump in garbage": 0}
        if age > 5:
            s["Repair"] -= 30
    if age > 8:  # old devices are poor repair or resale candidates
        s["Repair"] -= 25
        s["Resell or donate"] -= 25
    if damaged:  # swollen or leaking battery: only safe recycling is allowed
        s["Repair"] = 0
        s["Resell or donate"] = 0
        s["Authorised recycling"] = 100
    return {k: max(v, 0) for k, v in s.items()}


def next_saturday():
    today = dt.date.today()
    return today + dt.timedelta(days=(5 - today.weekday()) % 7 or 7)


def add_to_batch():
    r = st.session_state.result
    st.session_state.reqs[r["area"]][0] += r["qty"]
    st.session_state.reqs[r["area"]][1] += r["kg"]
    t = st.session_state.tot
    t["items"] += r["qty"]
    t["kg"] += r["kg"]
    t["co2"] += r["co2"]
    t["copper"] += r["copper"]
    st.session_state.added = True


def reset():
    st.session_state.reqs = copy.deepcopy(SEED["reqs"])
    st.session_state.tot = copy.deepcopy(SEED["tot"])
    st.session_state.result = None
    st.session_state.added = False


if "reqs" not in st.session_state:
    reset()

# ---------------------------------------------------------------- page
st.title("♻️ ReCircuit")
st.caption("Give every old device the right next life. Ranks repair, reuse and recycling by "
           "environmental impact, shows the materials inside, and groups recycling into one pickup per area.")

tab_check, tab_pickup, tab_impact, tab_flow = st.tabs(
    ["Check a device", "Pickup planner", "Impact so far", "How it works"])

# ---- tab 1: decision
with tab_check:
    left, right = st.columns([5, 6], gap="large")
    with left:
        st.subheader("Device details")
        name = st.selectbox("Device", list(DEVICES))
        c1, c2 = st.columns(2)
        age = c1.number_input("Age (years)", 0, 20, 4)
        qty = c2.number_input("Quantity", 1, 20, 1)
        condition = st.selectbox("Condition", ["Works fine", "Partly working", "Dead"])
        area = st.selectbox("Hostel or area", AREAS)
        dev = DEVICES[name]
        damaged = st.checkbox("Battery is swollen, hot or leaking") if dev["battery"] else False
        if st.button("Get best route", type="primary"):
            scores = score_routes(condition, age, damaged)
            ranked = sorted(scores, key=scores.get, reverse=True)
            best = ranked[0]
            st.session_state.added = False
            st.session_state.result = dict(
                name=name, qty=qty, area=area, damaged=damaged, scores=scores, ranked=ranked, best=best,
                kg=dev["kg"] * qty, co2=dev["co2"] * qty * SAVING[best],
                copper=dev["mats"]["Copper"] * qty * RECOVERY,
                mats={m: g * qty * RECOVERY for m, g in dev["mats"].items() if g > 0},
                footprint=dev["co2"] * qty,
            )

    with right:
        st.subheader("Recommendation")
        r = st.session_state.result
        if not r:
            st.info("Enter a device on the left and press Get best route.")
        else:
            st.success(f"Best route: **{r['best']}**. {WHY[r['best']]}")
            if r["damaged"]:
                st.error("Damaged battery: do not charge or crush it. Keep it in a dry, non-flammable "
                         "container away from heat and drop it only in the special-handling box.")
            for route in r["ranked"]:
                a, b, c = st.columns([3, 4, 2])
                a.write(f"**{route}**" if route == r["best"] else route)
                b.progress(r["scores"][route] / 100)
                c.write(f"{round(r['footprint'] * SAVING[route])} kg CO2")
            m1, m2 = st.columns(2)
            m1.metric("CO2 avoided (best route)", f"{round(r['co2'])} kg")
            m2.metric("E-waste kept out of landfill", f"{r['kg']:.1f} kg")
            st.write("**Inside this batch (about 80% recoverable by recycling):**")
            st.write(", ".join(f"{m}: {g:.2f} g" if g < 1 else f"{m}: {g:.0f} g" for m, g in r["mats"].items()))
            if r["best"] == "Authorised recycling":
                if st.session_state.added:
                    st.success(f"Added to the {r['area']} batch.")
                else:
                    st.button(f"Add {r['qty']} item(s) to {r['area']} pickup batch", on_click=add_to_batch)
            else:
                st.caption("This item goes through repair or reuse, so it does not join the recycling batch.")

# ---- tab 2: pickup planner
with tab_pickup:
    st.subheader("Community pickup planner")
    st.write(f"A pickup is proposed once an area reaches **{PICKUP_THRESHOLD}** items for recycling. "
             "One trip replaces many small ones.")
    for a in AREAS:
        n, kg = st.session_state.reqs[a]
        ready = n >= PICKUP_THRESHOLD
        st.markdown(f"**{a}** - {'Pickup ready' if ready else f'{PICKUP_THRESHOLD - n} more needed'}")
        st.progress(min(n / PICKUP_THRESHOLD, 1.0))
        msg = f"{n} items, {kg:.1f} kg"
        if ready:
            msg += (f". Proposed pickup: {next_saturday():%A, %d %B}. List sent to a sample authorised "
                    "recycler (replace with a CPCB-listed unit).")
        st.caption(msg)
    st.button("Reset sample data", on_click=reset)

# ---- tab 3: impact
with tab_impact:
    st.subheader("Impact so far")
    t = st.session_state.tot
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Items handled", t["items"])
    k2.metric("E-waste collected", f"{t['kg']:.0f} kg")
    k3.metric("CO2 avoided", f"{round(t['co2'])} kg")
    k4.metric("Copper recoverable", f"{t['copper'] / 1000:.2f} kg")
    st.caption("Sample data. Replace the factors in this file with cited values before submitting.")

# ---- tab 4: flowchart
with tab_flow:
    st.subheader("How the system works")
    st.graphviz_chart("""
    digraph G {
      rankdir=TD; node [shape=box, style="rounded,filled", fillcolor="#e0f1f3", fontname="Helvetica"];
      A [label="User enters device type, age,\\ncondition, quantity, area"];
      B [label="Rule table scores repair, resell or\\ndonate, recycle, dump"];
      C [label="Battery swollen or leaking?", shape=diamond];
      D [label="Force safe recycling\\nwith handling warning"];
      E [label="Rank routes,\\nreuse above recycling"];
      F [label="Show materials inside\\nand CO2 avoided"];
      G [label="Best route is recycling?", shape=diamond];
      H [label="Add to area batch"];
      I [label="Show repair or reuse advice"];
      J [label="Batch reached minimum quantity?", shape=diamond];
      K [label="Propose one pickup date and send\\nlist to authorised recycler"];
      L [label="Keep collecting"];
      A -> B -> C; C -> D [label="yes"]; C -> E [label="no"]; D -> F; E -> F; F -> G;
      G -> H [label="yes"]; G -> I [label="no"]; H -> J; J -> K [label="yes"]; J -> L [label="no"];
    }
    """)
