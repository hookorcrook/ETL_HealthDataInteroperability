from pyspark.sql import SparkSession
from datetime import datetime
import os
import requests
import json



timestamp = datetime.now().strftime("%Y%m%d")
transformed_path = f"./include/temp_data/patients_ready_{timestamp}.json"

#api_token = "d2p_afc0zYTgYyGErraPlIv83JFiKv0Vyh7nHHu8mG8fFzoJ2dXRgT"
#api_token = "d2p_aPUJ1qzqSrSiBSPFDcSq2qx7l8tv6YEtPQMdhGSmF2Yu2FLdb4"
api_token = "d2p_YbLjXF742weKOQqB1vLjqLI3CBH67tidXDKgL7cuuvzm0ztdVh"
base_url = "http://web:8080"


spark = SparkSession.builder.appName("LoadPatientDHIS2").master("local[*]").getOrCreate()

print(f"✅ Spark session started", flush=True)


headers = {
    "Authorization": f"ApiToken {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}


def get_or_create_program(name="Patient Tracking Program", tracked_entity_type_id=None, org_unit_id=None):
    url = f"{base_url}/api/programs.json?fields=id,name&paging=false"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    programs = response.json().get("programs", [])

    for prog in programs:
        if prog["name"] == name:
            print(f"✅ Program '{name}' already exists -> {prog['id']}", flush=True)

            # Check current org units
            program_details_resp = requests.get(
                f"{base_url}/api/programs/{prog['id']}?fields=id,name,organisationUnits[id]",
                headers=headers
            )
            program_details_resp.raise_for_status()
            program_details = program_details_resp.json()
            existing_ous = {ou["id"] for ou in program_details.get("organisationUnits", [])}

            if org_unit_id:
                if org_unit_id not in existing_ous:
                    print(f"➕ OrgUnit {org_unit_id} not found, patching program", flush=True)
                    updated_ous = [{"id": ou} for ou in existing_ous.union({org_unit_id})]

                    patch_payload = {
                        "organisationUnits": updated_ous
                    }

                    patch_response = requests.patch(
                        f"{base_url}/api/programs/{prog['id']}",
                        headers=headers,
                        json=patch_payload
                    )
                    patch_response.raise_for_status()
                    print(f"✅ Patched program with new OrgUnit", flush=True)
                else:
                    print(f"✅ OrgUnit {org_unit_id} already linked to program", flush=True)

            return prog["id"]

    # If not found, create new program
    if not tracked_entity_type_id:
        raise ValueError("tracked_entity_type_id is required to create a new program")

    payload = {
        "name": name,
        "shortName": name[:50],
        "description": f"{name} for tracking patients",
        "programType": "WITH_REGISTRATION",
        "trackedEntityType": {"id": tracked_entity_type_id},
        "organisationUnits": [{"id": org_unit_id}] if org_unit_id else [],
        "enrollmentDateLabel": "Enrollment Date",
        "incidentDateLabel": "Incident Date",
        "selectEnrollmentDatesInFuture": False,
        "selectIncidentDatesInFuture": False,
        "onlyEnrollOnce": False
    }

    print("📤 Creating Program:", json.dumps(payload, indent=2), flush=True)
    response = requests.post(f"{base_url}/api/programs", headers=headers, json=payload)
    response.raise_for_status()

    new_id = response.json()["response"]["uid"]
    print(f"✅ Created Program '{name}' -> {new_id}", flush=True)
    return new_id



def get_or_create_tracked_entity_type(display_name="Person", attribute_ids=None):
    url = f"{base_url}/api/trackedEntityTypes.json?fields=id,displayName"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    for entity in response.json().get("trackedEntityTypes", []):
        if entity["displayName"] == display_name:
            print(f"✅ TrackedEntityType '{display_name}' already exists -> {entity['id']}", flush=True)
            return entity["id"]

    # Fix: wrap each attr_id in {"id": attr_id}
    payload = {
        "name": display_name,
        "shortName": display_name[:50],
        "description": f"{display_name} tracked entity",
        "trackedEntityTypeAttributes": [
            {"trackedEntityAttribute": {"id": attr_id}} for attr_id in (attribute_ids or [])
        ]
    }

    print("📤 Payload:", json.dumps(payload, indent=2), flush=True)

    response = requests.post(f"{base_url}/api/trackedEntityTypes", headers=headers, json=payload)
    response.raise_for_status()

    print("📥 Response:", json.dumps(response.json(), indent=2), flush=True)
    new_id = response.json()["response"]["uid"]
    print(f"✅ Created new TrackedEntityType '{display_name}' with ID: {new_id}", flush=True)
    return new_id


def get_or_create_parent_org_unit(name="National", short_name="NATIONAL", opening_date="1990-01-01"):
    """Creates or returns the ID of the top-level parent Org Unit"""
    url = f"{base_url}/api/organisationUnits.json?fields=id,displayName&paging=false"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    for unit in response.json().get("organisationUnits", []):
        if unit["displayName"] == name:
            print(f"✅ Parent OrgUnit found: {name} (ID: {unit['id']})", flush=True)
            return unit["id"]

    # If not found, create it as a root org unit (no parent)
    payload = {
        "name": name,
        "shortName": short_name,
        "openingDate": opening_date
    }
    response = requests.post(f"{base_url}/api/organisationUnits", headers=headers, json=payload)
    response.raise_for_status()

    new_id = response.json()["response"]["uid"]
    print(f"✅ Created parent OrgUnit '{name}' with ID: {new_id}", flush=True)
    return new_id


def get_or_create_org_unit(name="Default Hospital", short_name="Default", opening_date="2000-01-01", org_unit_id=None):
    # Create or get parent first
    parent_id = get_or_create_parent_org_unit()

    # If ID is given, check if org unit exists
    if org_unit_id:
        url_id = f"{base_url}/api/organisationUnits/{org_unit_id}.json?fields=id,name,shortName,openingDate,parent[id]"
        response = requests.get(url_id, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            org_unit = response.json()
            print(org_unit)
            current_parent = org_unit.get("parent", {}).get("id")
            if current_parent != parent_id:
                # Update the parent to the correct one and send full org unit with PUT
                org_unit["parent"] = {"id": parent_id}

                put_response = requests.put(
                    f"{base_url}/api/organisationUnits/{org_unit_id}",
                    headers=headers,
                    json=org_unit
                )
                put_response.raise_for_status()
                print(f"🔄 Updated OrgUnit {org_unit_id} to have parent {parent_id}", flush=True)
            else:
                print(f"✅ OrgUnit found by ID: {org_unit_id} with correct parent", flush=True)
            return org_unit_id

    # Check by name
    url = f"{base_url}/api/organisationUnits.json?fields=id,displayName,shortName,openingDate,parent[id]&paging=false"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    for unit in response.json().get("organisationUnits", []):
        if unit["displayName"] == name:
            unit_id = unit["id"]
            current_parent = unit.get("parent", {}).get("id")
            if current_parent != parent_id:
                # Fetch full org unit for PUT update
                url_unit = f"{base_url}/api/organisationUnits/{unit_id}.json?fields=id,name,shortName,openingDate,parent[id]"
                unit_response = requests.get(url_unit, headers=headers)
                unit_response.raise_for_status()
                org_unit = unit_response.json()
                org_unit["parent"] = {"id": parent_id}

                put_response = requests.put(
                    f"{base_url}/api/organisationUnits/{unit_id}",
                    headers=headers,
                    json=org_unit
                )
                put_response.raise_for_status()
                print(f"🔄 Updated OrgUnit '{name}' to have parent {parent_id}", flush=True)
            else:
                print(f"✅ OrgUnit found by name: {name} (ID: {unit_id}) with correct parent", flush=True)
            return unit_id

    # Create new Org Unit
    payload = {
        "name": name,
        "shortName": short_name,
        "openingDate": opening_date,
        "parent": {
            "id": parent_id
        }
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


def tracked_entity_exists_by_patient_id(org_unit_id, tracked_entity_type, patient_id_attr_id, patient_id_value):
    url = (
        f"{base_url}/api/trackedEntityInstances.json"
        f"?ou={org_unit_id}"
        f"&trackedEntityType={tracked_entity_type}"
        f"&filter={patient_id_attr_id}:EQ:{patient_id_value}"
        f"&paging=false"
        f"&fields=trackedEntityInstance"
    )

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    results = response.json().get("trackedEntityInstances", [])
    return results[0]["trackedEntityInstance"] if results else None

def patch_user_org_units(username="admin", org_unit_id=None):
    if not org_unit_id:
        org_unit_id = get_or_create_org_unit()

    # Get user UID by username
    user_url = f"{base_url}/api/users.json?filter=username:eq:{username}&fields=id,username&paging=false"
    response = requests.get(user_url, headers=headers)
    response.raise_for_status()
    users = response.json().get("users", [])

    if not users:
        print(f"❌ No user found with username '{username}'", flush=True)
        return

    user_id = users[0]["id"]
    print(f"🔧 Found user '{username}' with ID: {user_id}", flush=True)

    # patch_payload = {
    #     "organisationUnits": [{"id": org_unit_id}],
    #     "dataViewOrganisationUnits": [{"id": org_unit_id}],
    #     "teiSearchOrganisationUnits": [{"id": org_unit_id}]
    # }

    patch_payload = [
    { "op": "replace", "path": "/organisationUnits", "value": [{"id": org_unit_id}] },
    { "op": "replace", "path": "/dataViewOrganisationUnits", "value": [{"id": org_unit_id}] },
    { "op": "replace", "path": "/teiSearchOrganisationUnits", "value": [{"id": org_unit_id}] }
    ]

    header_patch = {
    "Authorization": f"ApiToken {api_token}",
    "Content-Type": "application/json-patch+json",
    "Accept": "application/json"}

    patch_url = f"{base_url}/api/users/{user_id}"
    patch_response = requests.patch(patch_url, headers=header_patch, json=patch_payload)

    if patch_response.status_code in [200, 204]:
        print(f"✅ Successfully patched user '{username}' with OrgUnit {org_unit_id}", flush=True)
    else:
        print(f"❌ Failed to patch user '{username}': {patch_response.status_code} - {patch_response.text}", flush=True)


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

    username = "admin"

    patch_user_org_units(username=username, org_unit_id=org_unit_id)

    program_id = get_or_create_program(tracked_entity_type_id=tracked_entity_type_id, org_unit_id=org_unit_id)
    print(f"✅ Program ID: {program_id}", flush=True)


    print(f"Processing for patient data load now", flush=True)

    with open(filepath) as f:
        patients = json.load(f)

    for patient in patients:
        # 🔍 Check if patient already exists
        existing_tei  = tracked_entity_exists_by_patient_id(org_unit_id,tracked_entity_type_id,attr_patient_id,patient["patient_id"])
        if existing_tei:
            print(f"⚠️ Patient {patient['patient_id']} already exists in DHIS2 as TEI: {existing_tei}.", flush=True)

            # 🔍 Check if TEI is already enrolled in the program
            enrollments_response = requests.get(
            f"{base_url}/api/enrollments.json?trackedEntityInstance={existing_tei}&program={program_id}&ou={org_unit_id}",
            headers=headers)

            if enrollments_response.status_code == 200:
                enrollments_data = enrollments_response.json()
                if enrollments_data.get("enrollments"):
                    print(f"✅ TEI {existing_tei} is already enrolled in the program {program_id}", flush=True)
                    continue
                else:
                    print(f"➕ Enrolling existing TEI {existing_tei} in program {program_id}", flush=True)
            else:
                print(f"❌ Failed to check enrollments for TEI {existing_tei}: {enrollments_response.status_code}", flush=True)

            # Proceed to enroll the existing TEI
            enrollment_payload = {
                "trackedEntityInstance": existing_tei,
                "program": program_id,
                "orgUnit": org_unit_id,
                "enrollmentDate": datetime.now().strftime("%Y-%m-%d"),
                "incidentDate": datetime.now().strftime("%Y-%m-%d")
                }

            enroll_response = requests.post(
                f"{base_url}/api/enrollments",
                headers=headers,
                json=enrollment_payload
            )

            if enroll_response.status_code in [200, 201]:
                print(f"✅ Enrolled existing TEI {existing_tei} in program {program_id}", flush=True)
            else:
                print(f"❌ Failed to enroll existing TEI {existing_tei}: {enroll_response.status_code} - {enroll_response.text}", flush=True)

            continue  # Skip to next patient

        print(f"🔍 Patient {patient['patient_id']} does not exist in DHIS2. Preparing to post...", flush=True)
        # Construct payload
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
            tei_id = response.json()["response"]["importSummaries"][0]["reference"]
            print(f"✅ Posted {patient['patient_id']} - TEI ID: {tei_id}", flush=True)

        # 🔁 Enroll TEI into the program
            enrollment_payload = {
                "trackedEntityInstance": tei_id,
                "program": program_id,
                "orgUnit": org_unit_id,
                "enrollmentDate": datetime.now().strftime("%Y-%m-%d"),
                 "incidentDate": datetime.now().strftime("%Y-%m-%d")
                }

            enroll_response = requests.post(
                f"{base_url}/api/enrollments",
                headers=headers,
                json=enrollment_payload
                )

        if enroll_response.status_code in [200, 201]:
            print(f"✅ Enrolled TEI {tei_id} in program {program_id}", flush=True)
        else:
            print(f"❌ Failed to enroll TEI {tei_id}: {enroll_response.status_code} - {enroll_response.text}", flush=True)


try:
    print("🚀 Starting DHIS2 load job...", flush=True)
    load_to_dhis2(filepath=transformed_path)
except Exception as e:
    print(f"❌ Error in load_to_dhis2: {e}", flush=True)
    raise


