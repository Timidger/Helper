"""This script will login to MyNeu using the credentials in "NEU_login.txt"""
#! /usr/bin/env python3

import os
from itertools import zip_longest
from selenium import webdriver
from selenium.common.exceptions import (UnexpectedTagNameException,
                                       WebDriverException)


LOGIN_PAGE = "http://myneu.neu.edu/cp/home/displaylogin"


def grouper(iterable, n, fillvalue=None):
    "Given an iterable, returns an iterable with sub-lists with a length of n"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

def get_login_credentials(file_name):
    """
    Retrieves the login credentials from the given file.
    The file should be formatted so that the first line contains the username
    and the second should contain the password (plaintext).
    """
    assert os.path.exists(file_name), "{} does not exist!".format(file_name)
    with open(file_name, "r") as login_file:
        contents = login_file.readlines()
    username, password = contents
    return username.strip(), password.strip()

def login(username, password):
    """
    Using the given username and password, logs into MyNEU through a
    selenium driver (firefox). Returns the driver object
    """
    driver = webdriver.Firefox()
    # Go to the login page
    login_page = driver.get(LOGIN_PAGE)

    # Find the user and password forms
    user_form = driver.find_element_by_id("user")
    pass_form = driver.find_element_by_id("pass")

    # Login in with the given credentias
    user_form.send_keys(username)
    pass_form.send_keys(password)

    # Click the login button
    button_class = driver.find_element_by_class_name("buttons")
    button = button_class.find_element_by_tag_name("input")
    button.click()

    # Return the driver so we can do more with it
    return driver

def get_self_service_page(driver):
    """
    Navigates the driver to the self-service page of MyNEU.
    """
    # Get the top tag tree (MyNEU Central, Self-Service, Commmunity, etc.)
    tabs = driver.find_element_by_id("tabs_tda")

    # Find the tab with the text "Self-Service"
    # Only searches the other tags, not the current one
    for tag in tabs.find_elements_by_class_name("taboff"):
        self_service_tag = tag.find_element_by_id("tab")
        if self_service_tag.text == "Self-Service":
            break
    else:
        # If can't find the tag, just raise an exception.
        # If this occurs, check if they rearranged the order of the tags
        raise UnexpectedTagNameException("Couldn't find Self-Service Tag")

    # Click on the tag to navigate to the other page
    self_service_tag.click()

def get_self_service_sections(driver):
    """
    Returns the various sections of the self-service tab as a dictionary
    ({title: selenium WebElement}).
    """
    # Get the big part of the page table we care about
    page_table = driver.find_element_by_class_name("uportal-background-content")
    # Get the <tr> tag of that table, which oddly has the same class name
    page_tr = page_table.find_element_by_class_name("uportal-background-content")

    # Get the first batch of section titles
    sections1 = page_tr.find_elements_by_class_name("uportal-head14-bold")
    # Make a dictionary where the key is the title and the value is the element
    sections1 = {element.text:element for element in sections1}

    # Get the second batch, which have their own formatting to stand out
    # since they are about financial services and that is important
    sections2 = page_tr.find_elements_by_class_name("Taupe")
    # Make a dictionary where the key is the title and the value is the element
    # These sections are all in caps, we'll just make them titled like the rest
    sections2 = {element.text.title(): element for element in sections2}

    # Now join the two sections together using magic and return
    sections = dict(sections1, **sections2)
    return sections

def get_self_service_section(driver, section):
    """
    Searches the sections of the self-service tab for the given section.
    If it can be found, the selenium WebElement it is attached to
    is returned as well. Casing is ignored in the search.
    """
    section = section.lower() # Casing doesn't matter to us
    sections = get_self_service_sections(driver) # This returns {str, element}
    for title, element in sections.items():
        # Lower the title for each section so we ignore casing
        if title.lower() == section:
            return element
    else:
        raise WebDriverException('Could not find section "{}"'.format(section))

def find_link(driver, link_name):
    """
    Searches through the text of all the links and returns the Selenium
    WebElement of the first one it finds. Casing is ignored in the search.
    """
    link_name = link_name.lower()
    for link in driver.find_elements_by_tag_name("a"):
        if link.text.lower() == link_name:
            return link

def correct_link(link_url: str):
    """
    Instead of simply clicking on the link, we need to check if there is
    JavaScript in the link that will open it up in a new window. If there
    is, we need to open the url directly. This function corrects the link
    (if it needs to be corrected) and then returns it.
    """
    if "javascript:OpenWinNEU" in link_url:
        if "http://" not in link_url and "https://" not in link_url:
            raise WebDriverException("This is javascript that does not have"
                                    " a url. There is nothing I can do")
        # The javascript is in the format "javascript:OpenWinNEU('...')"
        # So just find where the parens are, we have the url inside
        # The +/- 1 is to offset the quote ('), which may cause issues
        start = link_url.find("(") + 2
        end = link_url.rfind(")") - 1
        link_url = link_url[start:end]
    return link_url

def get_balance_data(driver):
    """
    Returns a big dictionary which contains data from the Husky Card  Account
    Balances page. The key contains what the data is about, and the value is
    the data itself.
    """
    contents = {}
    for element1 in driver.find_elements_by_tag_name("blockquote"):
        if element1.find_elements_by_class_name("Title"):
            for element2 in element1.find_elements_by_tag_name("table"):
                contents.update({k.text: v.text for k,v in grouper(element2.find_elements_by_class_name("Content"), 2)})
    return contents

def get_dining_dollars(driver):
    # Get the Husky Card Center section of the self-service tab
    # This is a selenium element
    assert driver.title == 'myNEU: View HuskyCard Balances', (
    "You need to be on the Husky Account Balance Page!")
    data = get_balance_data(driver)
    return data.get("Spring 15 Meal Plan")


if __name__ == "__main__":
    username, password = get_login_credentials("creds.txt")
    driver = login(username, password)
    get_self_service_page(driver)
    link = find_link(driver, "husky card account balances").get_attribute("href")
    driver.get(correct_link(link))
    print(get_dining_dollars(driver))
