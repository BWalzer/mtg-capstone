import json
import boto3
from bs4 import BeautifulSoup
import deck_scraping
import card_scraping


def split_single_card_string(deck_id, card_string):
    """
    Turns a single card string line from a deck list into a tuple.

    INPUT:
        - deck_id: the unique deck id from mtgtop8 assosciated with this deck
        - card_string: the single row from the deck list

    OUTPUT:
        - user_card_count: a tuple of the form (deck_id, card_name, card_count)
    """
    card_count = int(card_string[0])
    card_name = card_string[2:]
    user_card_count = (int(deck_id), card_name, card_count)

    return user_card_count

def decklist_deconstructor(deck_id, deck_list):
    """
    Turns a single deck list into a list of tuples of (deck_id, card_name, card_count)

    INPUT:
        - deck_id: the unique deck id assosciated with this deck
        - deck_list: a list of card_strings, containing the card count and name
                     of each card in the deck

    OUTPUT:
        - user_card_counts: a list of tuples of (deck_id, card_name, card_count)
                            for the deck list
    """
    user_card_counts = []
    for card_string in deck_list:
        # not worrying about sideboards for now
        if card_string[0] == 'S':
            break

        user_card_count = split_single_card_string(deck_id, card_string)
        user_card_counts.append(user_card_count)

    return user_card_counts

# def make_user_card_counts(deck_lists):
#     """
#     Takes in a bunch of deck lists and returns a list of user_card_counts.
#
#     INPUT:
#         - deck_lists: a list of deck lists from the deck_scraping
#
#     OUTPUT:
#         - user_card_counts: list of tuples of (deck_id, card_name, card_count)
#                             for each deck list in deck_lists
#     """
#     user_card_counts = []
#     for deck_id, deck_list in deck_lists.items():
#         user_card_count = decklist_deconstructor(deck_id, deck_list)
#         user_card_counts.append(user_card_count)
#
#     return flatten(user_card_counts)

def make_user_card_counts(front_pages=[0], scraped_events, verbose=False):
    """
    Version 2. Creates the user_card_count pairs from deck lists and stores them
    in a data base.

    INPUT:
        - front_pages: list of integers for each front page to request. Each
                       value in the list will get 10 events. Default value: [0]
        - scraped_events: a set of event ids for events that have already been
                          scraped. Events with these ids will not be scraped again.
        - verbose: boolean indicating if status messages are printed to the
                   console. Default value: False
    OUTPUT:
        - scraped_events: a set of event ids for events that have already been
                          scraped. Events with these ids will not be scraped again.
                          Events scraped during this function will be added.

    Request front page
    Get event ids
    Request event
    Get deck ids
    Request deck
    Process deck
    Store user-card-count pairs in db
        Amazon RDS
        PostgreSQL
    """

    for page_number in front_pages:
        front_page = deck_scraping.modern_front_page_request(
                                       page_number=page_number, verbose=verbose)
        front_page_soup = BeautifulSoup(front_page.text, 'html.parser')
        event_ids = deck_scraping.get_event_ids(front_page=front_page_soup,
                                                verbose=verbose)

        for event_id in event_ids:
            if event_id in scraped_events:
                if verbose: print('event id {} has already been scraped'.format(event_id))
                break
            event_page = deck_scraping.event_request(event_id=event_id,
                                                    verbose=verbose)
            event_page_soup = BeautifulSoup(event_page.text, 'html.parser')
            deck_ids = deck_scraping.get_deck_ids(event_page=event_page_soup,
                                                  verbose=verbose)
            for deck_id in deck_ids:
                deck_list = deck_scraping.deck_request(deck_id=deck_id,
                                                       verbose=verbose)
                # saving decklists as text files
                save_decklists(deck_id, deck_list)

            scraped_events.add(event_id)

    return scraped_events


def save_decklists(deck_id, deck_list):
    """
    Saves a deck list as a text file in my s3 bucket.

    INPUT:
        - deck_id: the unique id for the deck list
        - deck_list: the deck list to be saved in the s3 bucket.

    OUTPUT:
        NONE
    """

    # s3 = boto3.client('s3')
    # bucketname = 'mtg-capstone'
    # filename = 'data/raw_deck_lists/deck_list_{}.txt'.format(deck_id)
    #
    # s3.put_object(Bucket=bucketname, Key=filename, Body=deck_list)


    print('\t\tSaved deck!')

if __name__ == '__main__':
    with open('../data/scraped_events.json', 'r') as f:
        scraped_events = set(json.load(f))

    print('Scraped events: {}'.format(scraped_events))
    updated_scraped_events = make_user_card_counts(front_pages=[0],
                                  scraped_events = scraped_events, verbose=True)

    print('Updated scraped events: {}'.format(updated_scraped_events))
    with open('../data/scraped_events.json', 'w') as f:
        json.dump(list(updated_scraped_events), f)
