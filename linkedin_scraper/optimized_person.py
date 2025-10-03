import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import sys
from .objects import Experience, Education, Scraper, Interest, Accomplishment, Contact
import os
from linkedin_scraper import selectors


class OptimizedPerson(Scraper):
    """
    Optimized LinkedIn Person scraper that extracts experience and education
    directly from the main profile page instead of navigating to detail pages.
    """

    __TOP_CARD = "main"
    __WAIT_FOR_ELEMENT_TIMEOUT = 1

    def __init__(
            self,
            linkedin_url=None,
            name=None,
            about=None,
            experiences=None,
            educations=None,
            interests=None,
            accomplishments=None,
            headline=None,
            contacts=None,
            driver=None,
            get=True,
            scrape=True,
            close_on_complete=True,
            connections=True,
    ):
        self.linkedin_url = linkedin_url
        self.name = name
        self.headline = headline
        self.about = about or []
        self.experiences = experiences or []
        self.educations = educations or []
        self.interests = interests or []
        self.accomplishments = accomplishments or []
        self.also_viewed_urls = []
        self.contacts = contacts or []

        if driver is None:
            try:
                if os.getenv("CHROMEDRIVER") == None:
                    driver_path = os.path.join(
                        os.path.dirname(__file__), "drivers/chromedriver"
                    )
                else:
                    driver_path = os.getenv("CHROMEDRIVER")

                driver = webdriver.Chrome(driver_path)
            except:
                driver = webdriver.Chrome()

        if get:
            driver.get(linkedin_url)

        self.driver = driver

        if scrape:
            self.scrape(close_on_complete, connections=connections)

    def add_about(self, about):
        self.about.append(about)

    def add_experience(self, experience):
        self.experiences.append(experience)

    def add_education(self, education):
        self.educations.append(education)

    def add_interest(self, interest):
        self.interests.append(interest)

    def add_accomplishment(self, accomplishment):
        self.accomplishments.append(accomplishment)

    def add_location(self, location):
        self.location = location

    def add_contact(self, contact):
        self.contacts.append(contact)

    def is_open_to_work(self):
        try:
            return "#OPEN_TO_WORK" in self.driver.find_element(By.CLASS_NAME,
                                                               "pv-top-card-profile-picture").find_element(By.TAG_NAME,
                                                                                                           "img").get_attribute(
                "title")
        except:
            return False

    def get_experiences_from_homepage(self):
        """
        Extract experience information directly from the main profile page
        instead of navigating to the details/experience page.
        """
        try:
            # Look for experience section on the main page
            experience_selectors = [
                "//section[contains(@data-section, 'experience')]",
                "//section[.//span[contains(text(), 'Experience')]]",
                "//div[@id='experience']",
                "//section[.//h2[contains(text(), 'Experience')]]",
                "//div[contains(@class, 'experience')]//div[contains(@class, 'pvs-list__container')]",
                "//main//section[.//span[text()='Experience']]"
            ]

            experience_section = None
            for selector in experience_selectors:
                try:
                    experience_section = self.driver.find_element(By.XPATH, selector)
                    break
                except NoSuchElementException:
                    continue

            if not experience_section:
                print("No experience section found on homepage")
                return

            # Look for experience items within the section
            experience_items = []
            item_selectors = [
                ".//div[contains(@class, 'pvs-list__paged-list-item')]",
                ".//li[contains(@class, 'pvs-list__paged-list-item')]",
                ".//div[contains(@class, 'experience-item')]",
                ".//div[@data-view-name='profile-component-entity']"
            ]

            for selector in item_selectors:
                try:
                    experience_items = experience_section.find_elements(By.XPATH, selector)
                    if experience_items:
                        break
                except NoSuchElementException:
                    continue

            if not experience_items:
                print("No experience items found in section")
                return

            for i, item in enumerate(experience_items):
                try:
                    self._parse_experience_item(item, i)
                except Exception as e:
                    print(f"Error parsing experience item {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error getting experiences from homepage: {e}")

    def _parse_experience_item(self, item, index):
        """Parse individual experience item from the homepage"""
        try:
            item_text = item.text.strip()
            if not item_text:
                return

            # links = item.find_elements(By.TAG_NAME, "a")
            # spans = item.find_elements(By.TAG_NAME, "span")

            lines = [line.strip() for line in item_text.split('\n') if line.strip()]

            if len(lines) >= 2:
                position_title = lines[0] if lines[0] else ""
                company = lines[1] if len(lines) > 1 else ""

                # Look for date patterns in the text
                duration = None
                location = None
                description = ""

                for line in lines[2:]:
                    # Simple heuristics to identify different types of information
                    if any(month in line for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) or \
                            any(word in line for word in ['yrs', 'mos', 'year', 'month']):
                        duration = line
                    elif any(indicator in line.lower() for indicator in [', ', 'remote', 'hybrid']):
                        location = line
                    else:
                        description += line + " "

                # Extract from/to dates from duration if available
                from_date = ""
                to_date = ""
                if duration:
                    if '–' in duration or '-' in duration:
                        parts = duration.replace('–', '-').split('-')
                        if len(parts) >= 2:
                            from_date = parts[0].strip()
                            to_date = parts[1].strip()

                experience = Experience(
                    position_title=position_title,
                    from_date=from_date,
                    to_date=to_date,
                    duration=duration,
                    location=location.strip() if location else None,
                    description=description.strip() if description else None,
                    institution_name=company,
                    linkedin_url=None  # Would need to extract from company link if available
                )

                self.add_experience(experience)

        except Exception as e:
            print(f"Error parsing experience item: {e}")

    def get_educations_from_homepage(self):
        """
        Extract education information directly from the main profile page
        instead of navigating to the details/education page.
        """
        try:
            education_selectors = [
                "//section[contains(@data-section, 'education')]",
                "//section[.//span[contains(text(), 'Education')]]",
                "//div[@id='education']",
                "//section[.//h2[contains(text(), 'Education')]]",
                "//div[contains(@class, 'education')]//div[contains(@class, 'pvs-list__container')]",
                "//main//section[.//span[text()='Education']]"
            ]

            education_section = None
            for selector in education_selectors:
                try:
                    education_section = self.driver.find_element(By.XPATH, selector)
                    break
                except NoSuchElementException:
                    continue

            if not education_section:
                print("No education section found on homepage")
                return

            education_items = []
            item_selectors = [
                ".//div[contains(@class, 'pvs-list__paged-list-item')]",
                ".//li[contains(@class, 'pvs-list__paged-list-item')]",
                ".//div[contains(@class, 'education-item')]",
                ".//div[@data-view-name='profile-component-entity']"
            ]

            for selector in item_selectors:
                try:
                    education_items = education_section.find_elements(By.XPATH, selector)
                    if education_items:
                        break
                except NoSuchElementException:
                    continue

            if not education_items:
                print("No education items found in section")
                return

            for i, item in enumerate(education_items):
                try:
                    self._parse_education_item(item, i)
                except Exception as e:
                    print(f"Error parsing education item {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error getting education from homepage: {e}")

    def _parse_education_item(self, item, index):
        """Parse individual education item from the homepage"""
        try:
            # Try to extract text content
            item_text = item.text.strip()
            if not item_text:
                return

            # Try to extract basic information from text
            lines = [line.strip() for line in item_text.split('\n') if line.strip()]

            if len(lines) >= 1:
                institution_name = lines[0] if lines[0] else ""
                degree = lines[1] if len(lines) > 1 else None

                # Look for date patterns in the text
                from_date = None
                to_date = None
                description = ""

                for line in lines[2:]:
                    # Simple heuristics to identify dates vs description
                    if any(year in line for year in ['2020', '2021', '2022', '2023', '2024', '2025']) or \
                            any(word in line for word in ['–', '-']) and len(line) < 20:
                        # Likely a date range
                        if '–' in line or '-' in line:
                            parts = line.replace('–', '-').split('-')
                            if len(parts) >= 2:
                                from_date = parts[0].strip()
                                to_date = parts[1].strip()
                    else:
                        description += line + " "

                education = Education(
                    from_date=from_date,
                    to_date=to_date,
                    description=description.strip() if description else None,
                    degree=degree,
                    institution_name=institution_name,
                    linkedin_url=None  # Would need to extract from institution link if available
                )

                self.add_education(education)

        except Exception as e:
            print(f"Error parsing education item: {e}")

    def get_name_and_location(self):
        try:
            top_panel = self.driver.find_element(By.XPATH, "//*[@class='mt2 relative']")
            self.name = top_panel.find_element(By.TAG_NAME, "h1").text
            self.location = top_panel.find_element(By.XPATH,
                                                   "//*[@class='text-body-small inline t-black--light break-words']").text
        except Exception as e:
            print(f"Error getting name and location: {e}")

    def get_headline(self):
        try:
            # Try to find the headline element - it's usually in a div with specific classes
            headline_selectors = [
                "//div[contains(@class, 'text-body-medium') and contains(@class, 'break-words')]",
                "//div[@class='text-body-medium break-words']",
                "//*[contains(@class, 'pv-text-details__left-panel')]//div[contains(@class, 'text-body-medium')]",
                "//section[contains(@class, 'pv-top-card')]//div[contains(@class, 'text-body-medium')]"
            ]

            for selector in headline_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # Filter out elements that are clearly not headlines
                        if (text and 0 < len(text) < 200 and  # Headlines are usually short
                                not text.startswith('http') and  # Not a URL
                                not text.isdigit() and  # Not just numbers
                                '·' not in text and  # Not location/connection info
                                'connections' not in text.lower() and
                                'followers' not in text.lower() and
                                text != self.name):  # Not the person's name
                            self.headline = text
                            return
                except NoSuchElementException:
                    continue

            # If no headline found with the above selectors, set to None
            self.headline = None

        except Exception as e:
            self.headline = None

    def get_about(self):
        try:
            about = self.driver.find_element(By.ID, "about").find_element(By.XPATH, "..").find_element(By.CLASS_NAME,
                                                                                                       "display-flex").text
        except NoSuchElementException:
            about = None
        self.about = about

    def scrape(self, close_on_complete=True, connections=True):
        if self.is_signed_in():
            self.scrape_logged_in(close_on_complete=close_on_complete, connections=connections)
        else:
            print("you are not logged in!")

    def scrape_logged_in(self, close_on_complete=True, connections=True):
        driver = self.driver

        WebDriverWait(driver, self.__WAIT_FOR_ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located(
                (
                    By.TAG_NAME,
                    self.__TOP_CARD,
                )
            )
        )
        self.wait(1)

        # get name and location
        self.get_name_and_location()

        # get headline
        self.get_headline()

        self.open_to_work = self.is_open_to_work()

        # get about
        self.get_about()

        # Scroll to load more content
        driver.execute_script(
            "window.scrollTo(0, Math.ceil(document.body.scrollHeight/2));"
        )
        driver.execute_script(
            "window.scrollTo(0, Math.ceil(document.body.scrollHeight/1.5));"
        )

        self.get_experiences_from_homepage()

        self.get_educations_from_homepage()

        # get interest (from main page)
        try:
            _ = WebDriverWait(driver, self.__WAIT_FOR_ELEMENT_TIMEOUT).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[@class='pv-profile-section pv-interests-section artdeco-container-card artdeco-card ember-view']",
                    )
                )
            )
            interestContainer = driver.find_element(By.XPATH,
                                                    "//*[@class='pv-profile-section pv-interests-section artdeco-container-card artdeco-card ember-view']"
                                                    )
            for interestElement in interestContainer.find_elements(By.XPATH,
                                                                   "//*[@class='pv-interest-entity pv-profile-section__card-item ember-view']"
                                                                   ):
                interest = Interest(
                    interestElement.find_element(By.TAG_NAME, "h3").text.strip()
                )
                self.add_interest(interest)
        except:
            pass

        # get accomplishment (from main page)
        try:
            _ = WebDriverWait(driver, self.__WAIT_FOR_ELEMENT_TIMEOUT).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[@class='pv-profile-section pv-accomplishments-section artdeco-container-card artdeco-card ember-view']",
                    )
                )
            )
            acc = driver.find_element(By.XPATH,
                                      "//*[@class='pv-profile-section pv-accomplishments-section artdeco-container-card artdeco-card ember-view']"
                                      )
            for block in acc.find_elements(By.XPATH,
                                           "//div[@class='pv-accomplishments-block__content break-words']"
                                           ):
                category = block.find_element(By.TAG_NAME, "h3")
                for title in block.find_element(By.TAG_NAME,
                                                "ul"
                                                ).find_elements(By.TAG_NAME, "li"):
                    accomplishment = Accomplishment(category.text, title.text)
                    self.add_accomplishment(accomplishment)
        except:
            pass

        # get connections (only if connections=True)
        if connections:
            try:
                driver.get("https://www.linkedin.com/mynetwork/invite-connect/connections/")
                _ = WebDriverWait(driver, self.__WAIT_FOR_ELEMENT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "mn-connections"))
                )
                connections_element = driver.find_element(By.CLASS_NAME, "mn-connections")
                if connections_element is not None:
                    for conn in connections_element.find_elements(By.CLASS_NAME, "mn-connection-card"):
                        anchor = conn.find_element(By.CLASS_NAME, "mn-connection-card__link")
                        url = anchor.get_attribute("href")
                        name = conn.find_element(By.CLASS_NAME, "mn-connection-card__details").find_element(
                            By.CLASS_NAME, "mn-connection-card__name").text.strip()
                        occupation = conn.find_element(By.CLASS_NAME, "mn-connection-card__details").find_element(
                            By.CLASS_NAME, "mn-connection-card__occupation").text.strip()

                        contact = Contact(name=name, occupation=occupation, url=url)
                        self.add_contact(contact)
            except:
                pass

        if close_on_complete:
            driver.quit()

    @property
    def company(self):
        if self.experiences:
            return (
                self.experiences[0].institution_name
                if self.experiences[0].institution_name
                else None
            )
        else:
            return None

    @property
    def job_title(self):
        if self.experiences:
            return (
                self.experiences[0].position_title
                if self.experiences[0].position_title
                else None
            )
        else:
            return None

    def __repr__(self):
        return "<OptimizedPerson {name}\n\nHeadline\n{headline}\n\nAbout\n{about}\n\nExperience\n{exp}\n\nEducation\n{edu}\n\nInterest\n{int}\n\nAccomplishments\n{acc}\n\nContacts\n{conn}>".format(
            name=self.name,
            headline=self.headline,
            about=self.about,
            exp=self.experiences,
            edu=self.educations,
            int=self.interests,
            acc=self.accomplishments,
            conn=self.contacts,
        )
