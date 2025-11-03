import sys
from time import sleep
from faker import Faker
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Check for command-line argument
if len(sys.argv) < 2:
    print("Usage: python selenium_bulk_load.py <number_of_patients>")
    sys.exit(1)

num_patients = int(sys.argv[1])
fake = Faker()

# Setup Chrome headless
options = webdriver.ChromeOptions()
#options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

created_patients = []

try:
    # Login
    driver.get("http://localhost:8081/openmrs/login.htm")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Inpatient Ward')]"))).click()
    driver.find_element(By.ID, "username").send_keys("admin")
    driver.find_element(By.ID, "password").send_keys("Admin123")
    driver.find_element(By.ID, "loginButton").click()

    # Navigate to home page after login
    #wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Home")))
    driver.get("http://localhost:8081/openmrs/referenceapplication/home.page")

    for _ in tqdm(range(num_patients), desc="Creating patients"):
        # Open "Register a Patient" tab
        driver.get("http://localhost:8081/openmrs/referenceapplication/home.page")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Register a patient')]"))).click()

        # Generate fake patient data
        first_name = fake.first_name()
        middle_name = fake.first_name()
        last_name = fake.last_name()
        gender = fake.random_element(elements=("M", "F"))
        age_years = fake.random_int(min=0, max=90)
        age_months = fake.random_int(min=0, max=11)
        address = {
            "address1": fake.street_address(),
            "cityVillage": fake.city(),
            "stateProvince": fake.state(),
            "country": fake.country(),
            "postalCode": fake.postcode()
        }
        phone_number = fake.msisdn()[:10]  # 10-digit phone

        # Step 1: Name
        wait.until(EC.presence_of_element_located((By.NAME, "givenName"))).send_keys(first_name)
        driver.find_element(By.NAME, "middleName").send_keys(middle_name)
        driver.find_element(By.NAME, "familyName").send_keys(last_name)
        driver.find_element(By.ID, "next-button").click()   

        # Step 2: Gender
        wait.until(EC.presence_of_element_located((By.ID, "gender-field")))
        gender_dropdown = driver.find_element(By.ID, "gender-field")
        for option in gender_dropdown.find_elements(By.TAG_NAME, 'option'):
            if option.get_attribute("value") == gender:
                option.click()
                break
        driver.find_element(By.ID, "next-button").click()

        # Step 3: Age
        wait.until(EC.presence_of_element_located((By.ID, "birthdateYears-field"))).send_keys(str(age_years))
        driver.find_element(By.ID, "birthdateMonths-field").send_keys(str(age_months))
        driver.find_element(By.ID, "next-button").click()

        # Step 4: Address
        wait.until(EC.presence_of_element_located((By.ID, "address1"))).send_keys(address["address1"])
        driver.find_element(By.ID, "cityVillage").send_keys(address["cityVillage"])
        driver.find_element(By.ID, "stateProvince").send_keys(address["stateProvince"])
        driver.find_element(By.ID, "country").send_keys(address["country"])
        driver.find_element(By.ID, "postalCode").send_keys(address["postalCode"])
        driver.find_element(By.ID, "next-button").click()

        # Step 5: Phone
        wait.until(EC.presence_of_element_located((By.NAME, "phoneNumber"))).send_keys(phone_number)
        driver.find_element(By.ID, "next-button").click()

        # Step 6: Skip relationships
        wait.until(EC.presence_of_element_located((By.ID, "next-button"))).click()

        # Step 7: Submit
        wait.until(EC.element_to_be_clickable((By.ID, "submit"))).click()

        # Log patient name
        full_name = f"{first_name} {middle_name} {last_name}"
        created_patients.append(full_name)

        # Small delay to ensure form submission and page reset
        sleep(1)

finally:
    driver.quit()
    print(f"\nCreated {len(created_patients)} Patient(s) Successfully Created in OpenMRS!:")
    for patient in created_patients:
        print(patient)
