# Nassau Candy Route Efficiency Project

## Run the dashboard

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Keep `shipment_legs.csv` in the same folder as `streamlit_app.py`.

## Main methodology

The supplied dates contain large, cohort-specific offsets. The project retains raw lead time for audit and uses operational lead time after removing the minimum offset in each Order ID year cohort. The resulting 0–11 day measure matches the expected ordering of the four ship modes.

Default delay threshold: more than 5 days. Route score: 50% lead time, 25% variability, and 25% delay frequency. Routes need at least five shipment legs to be ranked.
