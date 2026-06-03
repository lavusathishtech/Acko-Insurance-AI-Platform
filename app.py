import streamlit as st
import pandas as pd
import joblib

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="ACKO AI Premium Predictor",
    page_icon="🚗",
    layout="wide"
)

# =====================================================
# LOAD MODEL
# =====================================================

model = joblib.load("premium_model.pkl")

# =====================================================
# TITLE
# =====================================================

st.title("🛡️ ACKO AI Insurance Premium Predictor")

st.write(
    "Get instant AI-powered insurance premium estimates."
)

# =====================================================
# FORM
# =====================================================

with st.form("premium_form"):

    col1, col2 = st.columns(2)

    with col1:

        vehicle_make = st.selectbox(
            "Vehicle Make",
            ["Maruti", "Hyundai", "Honda", "Tata"]
        )

        vehicle_model = st.text_input(
            "Vehicle Model",
            "Swift"
        )

        manufacturing_year = st.number_input(
            "Manufacturing Year",
            2010,
            2025,
            2021
        )

        idv = st.number_input(
            "IDV",
            100000,
            5000000,
            400000
        )

    with col2:

        fuel_type = st.selectbox(
            "Fuel Type",
            ["Petrol", "Diesel", "Electric"]
        )

        policy_type = st.selectbox(
            "Policy Type",
            ["Comprehensive", "Third Party"]
        )

        ncb_percent = st.slider(
            "NCB %",
            0,
            50,
            20
        )

        claim_history_count = st.number_input(
            "Previous Claims",
            0,
            10,
            0
        )

    submit = st.form_submit_button(
        "Predict Premium"
    )

# =====================================================
# PREDICTION
# =====================================================

if submit:

    vehicle_age = 2025 - manufacturing_year

    input_df = pd.DataFrame([{

        'vehicle_make': vehicle_make,
        'vehicle_model': vehicle_model,
        'segment': 'hatchback',
        'fuel_type': fuel_type,
        'policy_type': policy_type,
        'state': 'Maharashtra',
        'previous_insurer': 'Acko',
        'customer_age': 35,
        'city_tier': 2,
        'city_risk_score': 1.0,
        'manufacturing_year': manufacturing_year,
        'vehicle_age_years': vehicle_age,
        'engine_cc': 1197,
        'idv': idv,
        'ncb_percent': ncb_percent,
        'claim_history_count': claim_history_count,
        'num_addons': 0

    }])

    premium = model.predict(input_df)[0]

    st.success(
        f"Estimated Premium: ₹{premium:,.0f}"
    )

    st.metric(
        "Annual Premium",
        f"₹{premium:,.0f}"
    )