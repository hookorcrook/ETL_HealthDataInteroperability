from pyspark.sql import SparkSession
from datetime import datetime
import os
import requests
import json



timestamp = datetime.now().strftime("%Y%m%d")
transformed_path = f"./include/temp_data/patients_ready_{timestamp}.json"

api_token = "d2p_afc0zYTgYyGErraPlIv83JFiKv0Vyh7nHHu8mG8fFzoJ2dXRgT"
base_url = "http://web:8080"


spark = SparkSession.builder.appName("LoadPatientDHIS2").master("local[*]").getOrCreate()

print(f"✅ Spark session started", flush=True)


headers = {
    "Authorization": f"ApiToken {api_token}",
    "Content-Type": "application/json"
}


def get_or_create_tracked_entity_type(display_name="Person", attribute_ids=None):
    url = f"{base_url}/api/trackedEntityTypes.json?fields=id,displayName"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    for entity in response.json().get("trackedEntityTypes", []):
        if entity["displayName"] == display_name:
            print(f"✅ TrackedEntityType '{display_name}' already exists -> {entity['id']}", flush=True)
            return entity["id"]

    # Create new trackedEntityType with attributes attached
    payload = {
        "name": display_name,
        "shortName": display_name[:50],
        "description": f"{display_name} tracked entity",
        "trackedEntityTypeAttributes": [
            {"trackedEntityAttribute": attr_id} for attr_id in (attribute_ids or [])
        ]
    }

    response = requests.post(f"{base_url}/api/trackedEntityTypes", headers=headers, json=payload)
    response.raise_for_status()
    new_id = response.json()["response"]["uid"]
    print(f"✅ Created new TrackedEntityType '{display_name}' with ID: {new_id}", flush=True)
    return new_id


def get_or_create_org_unit(name="Default Hospital", short_name="Default", opening_date="2000-01-01", org_unit_id=None):
    # Check by ID if provided
    if org_unit_id:
        url_id = f"{base_url}/api/organisationUnits/{org_unit_id}"
        response = requests.get(url_id, headers=headers)
        if response.status_code == 200:
            print(f"✅ OrgUnit found by ID: {org_unit_id}", flush=True)
            return org_unit_id

    # Check by name
    url = f"{base_url}/api/organisationUnits.json?fields=id,displayName&paging=false"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    for unit in response.json().get("organisationUnits", []):
        if unit["displayName"] == name:
            print(f"✅ OrgUnit found by name: {name} (ID: {unit['id']})", flush=True)
            return unit["id"]

    # Create new Org Unit
    payload = {
        "name": name,
        "shortName": short_name,
        "openingDate": opening_date
    }
    response = requests.post(f"{base_url}/api/organisationUnits", headers=headers, json=payload)
    response.raise_for_status()
    new_id = response.json()["response"]["uid"]
    print(f"✅ Created OrgUnit '{name}' with ID: {new_id}", flush=True)
    return new_id


def get_or_create_attribute(name, value_type):
    try:
        # 1. Check for existing attribute by name
        query_url = f"{base_url}/api/trackedEntityAttributes.json?filter=name:eq:{name}&fields=id,name,valueType"
        response = requests.get(query_url, headers=headers)
        response.raise_for_status()
        attributes = response.json().get("trackedEntityAttributes", [])
        print(f"🔍 Searching for attribute '{name}' with valueType '{value_type}' from {attributes}", flush=True)

        if attributes:
            existing = attributes[0]
            existing_id = existing["id"]

            if existing["valueType"] != value_type:
                print(f"❌ Conflict: existing attribute '{name}' has valueType '{existing['valueType']}' but expected '{value_type}'", flush=True)
                return None  # Skip or raise Exception based on use-case

            print(f"✅ Found existing attribute '{name}' -> {existing_id}", flush=True)
            return existing_id

        # 2. Create attribute if not found
        payload = {
            "name": name,
            "shortName": name[:50],
            "valueType": value_type,
            "aggregationType": "NONE",
            "orgunitScope": False,
            "inherit": False,
            "confidential": False,
            "unique": False
        }
        print(["Creating new attribute with payload:", payload], flush=True)

        post_url = f"{base_url}/api/trackedEntityAttributes"
        response = requests.post(post_url, headers=headers, json=payload)
        response.raise_for_status()

        new_id = response.json()["response"]["uid"]
        print(f"✅ Created new attribute '{name}' -> {new_id}", flush=True)
        return new_id

    except Exception as e:
        print(f"❌ Error creating or fetching attribute '{name}' from url {post_url}: {e}", flush=True)
        return None


def ensure_attributes_linked_to_tracked_entity_type(tracked_entity_type_id, attribute_ids):
    # Fetch the current trackedEntityType
    url = f"{base_url}/api/trackedEntityTypes/{tracked_entity_type_id}?fields=id,name,trackedEntityTypeAttributes[trackedEntityAttribute[id]]"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    tet_data = response.json()

    existing_attr_ids = {
        attr["trackedEntityAttribute"]["id"]
        for attr in tet_data.get("trackedEntityTypeAttributes", [])
    }

    new_attrs = [
        {"trackedEntityAttribute": {"id": attr_id}, "mandatory": False}
        for attr_id in attribute_ids if attr_id not in existing_attr_ids
    ]

    if not new_attrs:
        print(f"✅ All attributes already associated with TrackedEntityType {tracked_entity_type_id}", flush=True)
        return

    # Merge old and new attributes
    updated_attrs = tet_data.get("trackedEntityTypeAttributes", []) + new_attrs
    update_payload = {
        "name": tet_data["name"],
        "trackedEntityTypeAttributes": updated_attrs
    }

    put_url = f"{base_url}/api/trackedEntityTypes/{tracked_entity_type_id}"
    response = requests.put(put_url, headers=headers, json=update_payload)
    response.raise_for_status()
    print(f"✅ Linked missing attributes to TrackedEntityType {tracked_entity_type_id}", flush=True)


def load_to_dhis2(filepath):
    print(f"📦 Ensuring TrackedEntityAttributes exist...", flush=True)
    attr_name = get_or_create_attribute("Name", "TEXT")
    attr_patient_id = get_or_create_attribute("PatientID", "TEXT")
    attr_dob = get_or_create_attribute("DateOfBirth", "DATE")
    attr_gender = get_or_create_attribute("Gender", "TEXT")
    print(f"✅ Attributes created: {attr_name}, {attr_patient_id}, {attr_dob}, {attr_gender}", flush=True)
    attribute_ids = [attr_id for attr_id in [attr_name, attr_patient_id, attr_dob, attr_gender] if attr_id]

    tracked_entity_type_id = get_or_create_tracked_entity_type(attribute_ids=attribute_ids)
    print(f"✅ TrackedEntityType ID: {tracked_entity_type_id}", flush=True)

    # 🔁 Ensure attributes are linked to the trackedEntityType
    ensure_attributes_linked_to_tracked_entity_type(tracked_entity_type_id, attribute_ids)

    org_unit_id = get_or_create_org_unit()
    print(f"✅ OrgUnit ID: {org_unit_id}", flush=True)

    print(f"Processing for patient data load now", flush=True)

    with open(filepath) as f:
        patients = json.load(f)

    for patient in patients:
        payload = {
            "trackedEntityType": tracked_entity_type_id,
            "orgUnit": org_unit_id,
            "attributes": [
                {"attribute": attr_name, "value": patient["name"]},
                {"attribute": attr_patient_id, "value": patient["patient_id"]}
            ]
        }

        if patient.get("dob"):
            payload["attributes"].append({
                "attribute": attr_dob,
                "value": patient["dob"].split("T")[0]
            })

        if patient.get("gender"):
            payload["attributes"].append({
                "attribute": attr_gender,
                "value": patient["gender"]
            })

        print(f"Posting patient {patient['patient_id']} to DHIS2 with payload: {json.dumps(payload, indent=2)}", flush=True)
        # Post to DHIS2 API
        response = requests.post(
            f"{base_url}/api/trackedEntityInstances",
            headers=headers,
            json=payload
        )


        if response.status_code in [200, 201]:
            print(f"✅ Posted {patient['patient_id']} - {response.status_code}", flush=True)
            print(f"Response: {response.json()}", flush=True)
        else:
            print(f"❌ Failed for {patient['patient_id']}: {response.status_code} - {response.text}", flush=True)

try:
    print("🚀 Starting DHIS2 load job...", flush=True)
    load_to_dhis2(filepath=transformed_path)
except Exception as e:
    print(f"❌ Error in load_to_dhis2: {e}", flush=True)
    raise


