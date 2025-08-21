import json
import requests
import logging
import sys
from datetime import datetime
from faker import Faker
import random
from tqdm import tqdm

# Set up logging
import os

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'patient_bulk_load.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

# Initialize Faker
fake = Faker()

# Load configuration
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error(f"Configuration file not found at {config_path}")
    sys.exit(1)
except json.JSONDecodeError:
    logging.error(f"Invalid JSON in configuration file at {config_path}")
    sys.exit(1)

# OpenMRS API Configuration
OPENMRS_BASE_URL = f"{config['openmrs']['base_url']}/ws/rest/v1"
USERNAME = config['openmrs']['username']
PASSWORD = config['openmrs']['password']

def create_person(data):
    """Create a person in OpenMRS"""
    url = f"{OPENMRS_BASE_URL}/person"
    try:
        response = requests.post(
            url,
            json=data,
            auth=(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error creating person: {str(e)}")
        return None

def create_patient(person_data):
    """Create a patient using person data"""
    url = f"{config['openmrs']['base_url']}/registrationapp/registerPatient/submit.action"
    
    try:
        # Parse birthdate components
        birthdate = datetime.strptime(person_data["birthdate"], "%Y-%m-%d")
        
        # Form data with success URL parameter
        data = {
            # Person data from the UI format
            "givenName": person_data["names"][0]["givenName"],
            "middleName": person_data["names"][0].get("middleName", ""),
            "familyName": person_data["names"][0]["familyName"],
            "preferred": "true",
            "gender": person_data["gender"],
            "unknown": "false",
            "birthdateDay": str(birthdate.day),
            "birthdateMonth": str(birthdate.month),
            "birthdateYear": str(birthdate.year),
            "birthdateYears": "",
            "birthdateMonths": "",
            "birthdate": f"{birthdate.year}-{birthdate.month}-{birthdate.day}",
            
            # Address data
            "address1": person_data["addresses"][0]["address1"],
            "address2": person_data["addresses"][0].get("address2", ""),
            "cityVillage": person_data["addresses"][0]["cityVillage"],
            "stateProvince": person_data["addresses"][0]["stateProvince"],
            "country": person_data["addresses"][0]["country"],
            "postalCode": person_data["addresses"][0]["postalCode"],
            
            # Additional parameters
            "phoneNumber": f"0{random.randint(900000000, 999999999)}",  # Random phone number
            "relationship_type": "",
            "other_person_uuid": "",
            
            # App specific parameters
            "appId": "referenceapplication.registrationapp.registerPatient",
            "successUrl": f"{config['openmrs']['base_url']}/registrationapp/findPatient.page", # Where to redirect on success
            "returnUrl": f"{config['openmrs']['base_url']}/registrationapp/findPatient.page",  # Where to redirect on cancel
            # Additional required parameters from UI form
            "action": "submit",
            "identifierType": "05a29f94-c0ed-11e2-94be-8c13b969e334",  # OpenMRS ID
            "identifierTypeLocation": "44c3efb0-2583-4c80-a79e-1f756a03c0a1",  # Registration Desk
            "location": "b1a8b05e-3542-4037-bbd3-998ee9c40574",  # Inpatient Ward
            "ward": "b1a8b05e-3542-4037-bbd3-998ee9c40574"  # Inpatient Ward
        }
        
        logging.info(f"Attempting to create patient with data: {json.dumps(data, indent=2)}")
        
        # Create the patient
        response = requests.post(
            url,
            data=data,  # Using form data instead of JSON
            auth=(USERNAME, PASSWORD),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Check for specific error responses
        if response.status_code == 400:
            error_data = response.json()
            logging.error(f"Validation error: {json.dumps(error_data, indent=2)}")
            return None
        elif response.status_code == 500:
            logging.error("Server error. Response:")
            try:
                error_data = response.json()
                logging.error(json.dumps(error_data, indent=2))
            except:
                logging.error(response.text)
            return None
            
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error creating patient: {str(e)}")
        if hasattr(e.response, 'text'):
            logging.error(f"Server response: {e.response.text}")
        if hasattr(e.response, 'status_code'):
            logging.error(f"Status code: {e.response.status_code}")
        return None

def generate_patient_data():
    """Generate fake patient data"""
    gender = random.choice(['M', 'F'])
    
    # Generate similar names to what we see in the UI
    if gender == 'M':
        first_name = random.choice(['John', 'Shashwot', 'Khadga'])
        family_name = random.choice(['Doe', 'Musyaju', 'Oli'])
    else:
        first_name = random.choice(['Jane', 'Mary', 'Sarah'])
        family_name = random.choice(['Doe', 'Smith', 'Kumari'])
        
    # Generate a birthdate in a similar range to what we see in the UI
    birthdate = fake.date_between(start_date='-70y', end_date='-18y').strftime('%Y-%m-%d')
    
    person_data = {
        "names": [{
            "givenName": first_name,
            "familyName": fake.last_name(),
            "middleName": fake.first_name()
        }],
        "gender": gender,
        "birthdate": birthdate,
        "addresses": [{
            "address1": fake.street_address(),
            "cityVillage": fake.city(),
            "stateProvince": fake.state(),
            "country": fake.country(),
            "postalCode": fake.postcode()
        }]
    }
    return person_data

def bulk_load_synthetic_patients(num_patients):
    """Generate and load synthetic patients into OpenMRS"""
    successful_loads = 0
    failed_loads = 0
    
    logging.info(f"Starting bulk load of {num_patients} synthetic patients")
    
    # Use tqdm for progress bar
    for i in tqdm(range(num_patients), desc="Loading patients"):
        # Generate synthetic patient data
        person_data = generate_patient_data()
        
        # Create patient directly with person data
        patient_result = create_patient(person_data)
        if patient_result:
            successful_loads += 1
            logging.info(f"Successfully created patient")
        else:
            failed_loads += 1
            logging.error(f"Failed to create patient")

    # Print summary
    logging.info("\n=== Load Summary ===")
    logging.info(f"Total records processed: {num_patients}")
    logging.info(f"Successfully loaded: {successful_loads}")
    logging.info(f"Failed to load: {failed_loads}")
    logging.info(f"Success rate: {(successful_loads/num_patients)*100:.2f}%")

def validate_input(num_str):
    """Validate the input number of patients"""
    try:
        num = int(num_str)
        if num <= 0:
            raise ValueError("Number of patients must be positive")
        if num > 10000:
            response = input("Warning: Generating more than 10,000 patients may take a while. Continue? (y/n): ")
            if response.lower() != 'y':
                sys.exit(0)
        return num
    except ValueError as e:
        logging.error(f"Invalid input: {str(e)}")
        sys.exit(1)

def verify_openmrs_connection():
    """Verify that we can connect to OpenMRS and have necessary permissions"""
    try:
        # Test basic connection
        session = requests.Session()
        session.auth = (USERNAME, PASSWORD)
        
        # Test authentication
        test_url = f"{OPENMRS_BASE_URL}/session"
        response = session.get(test_url)
        response.raise_for_status()
        
        logging.info("Successfully connected to OpenMRS")
        return True
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to connect to OpenMRS: {str(e)}")
        if hasattr(e.response, 'text'):
            logging.error(f"Server response: {e.response.text}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bulk_load_patients.py <number_of_patients>")
        sys.exit(1)

    # Verify connection before proceeding
    if not verify_openmrs_connection():
        print("Failed to connect to OpenMRS. Please check the server connection and credentials.")
        sys.exit(1)

    num_patients = validate_input(sys.argv[1])
    bulk_load_synthetic_patients(num_patients)
