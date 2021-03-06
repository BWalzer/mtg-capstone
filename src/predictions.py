import psycopg2
import os
from deck_scraping import ReflexiveDict, parse_card_string
import numpy as np

class CardRecommender:

    def __init__(self):
        self._connect_to_db()
        self.feature_matrix = self._get_feature_matrix()
        self.card_dict = ReflexiveDict()
        self.all_cardstorm_ids = self.card_dict.get_cardstorm_ids()

    def _connect_to_db(self):
        db_name = os.environ['CARDSTORM_DB_DBNAME']
        db_host = os.environ['CARDSTORM_DB_HOST']
        db_username = os.environ['CARDSTORM_DB_USERNAME']
        db_password = os.environ['CARDSTORM_DB_PASSWORD']

        self.conn = psycopg2.connect('dbname={} host={} user={} password={}'.format(db_name, db_host, db_username, db_password))
        self.cursor = self.conn.cursor()

    def _get_feature_matrix(self):
        '''
        Gets the most recent feature matrix from the database and expands it.
        '''

        query = '''SELECT cardstorm_id, features
                   FROM product_matrices
                   WHERE run_id = (SELECT MAX(run_id) FROM product_matrices)
                   ORDER BY cardstorm_id ASC'''
        self.cursor.execute(query)

        feature_matrix = []

        for cardstorm_id, features in self.cursor.fetchall():
            feature_matrix.append(features)

        feature_matrix = np.array(feature_matrix)

        return feature_matrix

    def _fit(self, raw_deck_list):
        '''
        Solves for the 'u' vector, given d and V.

        make deck dictionary
        make deck vector
        solve for u

        '''

        deck_dict = self._deck_to_dict(raw_deck_list)
        self.deck_vector = self._vectorize_deck(deck_dict)


        # u vector from the equation d = u*V
        # print('feature_matrix: {}'.format(self.feature_matrix.shape))
        # print('deck_vector: {}'.format(self.deck_vector.shape))
        u_vector = np.linalg.lstsq(self.feature_matrix, self.deck_vector)[0]

        # recreated user deck list
        self.d_vector = np.dot(u_vector, self.feature_matrix.T)

    def recommend(self, raw_deck_list, land_filter=False, white_filter=False,
                  blue_filter=False, black_filter=False, red_filter=False,
                  green_filter=False, colorless_filter=False):
        '''
        Takes the dot product of u and V to get new ratings for the 'd' vector.
        '''
        self._fit(raw_deck_list)
        # print('raw: {}'.format(raw_deck_list))

        if raw_deck_list == '':
            self.cursor.execute('''SELECT cardstorm_id, SUM(card_count)
                                   FROM decks
                                   GROUP BY cardstorm_id
                                   ORDER BY sum DESC''')
            recommendations = [_[0] for _ in self.cursor.fetchall()]
        else:
            recommendations = self.all_cardstorm_ids[np.argsort(self.d_vector - self.deck_vector)[::-1]]

        # print('pre filter: {}'.format(len(recommendations)))
        if land_filter:
            recommendations = self._filter_lands(recommendations)
        if white_filter:
            recommendations = self._filter_white(recommendations)
        if blue_filter:
            recommendations = self._filter_blue(recommendations)
        if black_filter:
            recommendations = self._filter_black(recommendations)
        if red_filter:
            recommendations = self._filter_red(recommendations)
        if green_filter:
            recommendations = self._filter_green(recommendations)
        if colorless_filter:
            recommendations = self._filter_colorless(recommendations)

        # close connection when done
        self.conn.close()

        return recommendations

    def _filter_lands(self, recommendations):
        '''
        Takes the recommendations and remove all land cards.
        '''

        query = "SELECT cardstorm_id FROM cards WHERE type_line LIKE '%Land%' AND NOT type_line LIKE '%//%Land%'"

        self.cursor.execute(query)

        land_ids = {_[0] for _ in self.cursor.fetchall()}
        # print('land_ids: {}'.format(len(land_ids)))
        filtered_recommendations = [cardstorm_id for cardstorm_id in recommendations if not cardstorm_id in land_ids]

        return filtered_recommendations

    def _filter_white(self, recommendations):
        '''
        Takes the recommendations and remove all white cards.
        '''

        query = "SELECT cardstorm_id FROM cards WHERE 'W'=ANY(colors) AND type_line NOT LIKE '%Land%//%'"

        self.cursor.execute(query)

        white_ids = {_[0] for _ in self.cursor.fetchall()}
        # print('white: {}'.format(len(white_ids)))
        # print('\tpre-white: {}'.format(len(recommendations)))
        filtered_recommendations = [cardstorm_id for cardstorm_id in recommendations if not cardstorm_id in white_ids]
        # print('\tpost-white: {}'.format(len(filtered_recommendations)))

        return filtered_recommendations

    def _filter_blue(self, recommendations):
        '''
        Takes the recommendations and remove all blue cards.
        '''

        query = "SELECT cardstorm_id FROM cards WHERE 'U'=ANY(colors) AND type_line NOT LIKE '%Land%//%'"

        self.cursor.execute(query)

        blue_ids = {_[0] for _ in self.cursor.fetchall()}
        # print('blue: {}'.format(len(blue_ids)))

        # print('\tpre-blue: {}'.format(len(recommendations)))
        filtered_recommendations = [cardstorm_id for cardstorm_id in recommendations if not cardstorm_id in blue_ids]
        # print('\tpost-blue: {}'.format(len(filtered_recommendations)))

        return filtered_recommendations

    def _filter_black(self, recommendations):
        '''
        Takes the recommendations and remove all black cards.
        '''

        query = "SELECT cardstorm_id FROM cards WHERE 'B'=ANY(colors) AND type_line NOT LIKE '%Land%//%'"

        self.cursor.execute(query)

        black_ids = {_[0] for _ in self.cursor.fetchall()}
        # print('black: {}'.format(len(black_ids)))

        # print('\tpre-black: {}'.format(len(recommendations)))
        filtered_recommendations = [cardstorm_id for cardstorm_id in recommendations if not cardstorm_id in black_ids]
        # print('\tpost-black: {}'.format(len(filtered_recommendations)))

        return filtered_recommendations

    def _filter_red(self, recommendations):
        '''
        Takes the recommendations and remove all red cards.
        '''

        query = "SELECT cardstorm_id FROM cards WHERE 'R'=ANY(colors) AND type_line NOT LIKE '%Land%//%'"

        self.cursor.execute(query)

        red_ids = {_[0] for _ in self.cursor.fetchall()}

        # print('red: {}'.format(len(red_ids)))

        # print('\tpre-red: {}'.format(len(recommendations)))
        filtered_recommendations = [cardstorm_id for cardstorm_id in recommendations if not cardstorm_id in red_ids]
        # print('\tpost-red: {}'.format(len(filtered_recommendations)))

        return filtered_recommendations

    def _filter_green(self, recommendations):
        '''
        Takes the recommendations and remove all green cards.
        '''

        query = "SELECT cardstorm_id FROM cards WHERE 'G'=ANY(colors) AND type_line NOT LIKE '%Land%//%'"

        self.cursor.execute(query)

        green_ids = {_[0] for _ in self.cursor.fetchall()}

        # print('green: {}'.format(len(green_ids)))

        # print('\tpre-green: {}'.format(len(recommendations)))
        filtered_recommendations = [cardstorm_id for cardstorm_id in recommendations if not cardstorm_id in green_ids]
        # print('\tpost-green: {}'.format(len(filtered_recommendations)))

        return filtered_recommendations

    def _filter_colorless(self, recommendations):
        '''
        Takes the recommendations and remove all colorless cards.
        '''

        query = "SELECT cardstorm_id FROM cards WHERE array_length(colors, 1) IS NULL AND type_line NOT LIKE '%Land%//%' AND type_line NOT LIKE '%Land%'"

        self.cursor.execute(query)

        colorless_ids = {_[0] for _ in self.cursor.fetchall()}
        # print('colorless: {}'.format(len(colorless_ids)))

        # print('\tpre-colorless: {}'.format(len(recommendations)))
        filtered_recommendations = [cardstorm_id for cardstorm_id in recommendations if not cardstorm_id in colorless_ids]
        # print('\tpost-colorless: {}'.format(len(filtered_recommendations)))

        return filtered_recommendations

    def _vectorize_deck(self, deck_dict):
        '''
            Creates an (n x 1) vector, where n is the number of available cards

            INPUT:
                - deck_dict: dictionary, keys are cardstorm ids and values are card counts

            OUTPUT:
                - deck_vector: numpy array of shape (n x 1), where n is the number of
                                cardstorm_ids in all_cardstorm_ids. Each entry corresponds
                                to the corresponding cardstorm_id in all_cardstorm_ids,
                                and it is either the count of the card in the deck or 0
                                if it's not included in the deck.
        '''

        deck_vector = []

        for cardstorm_id in self.all_cardstorm_ids:
            if cardstorm_id in deck_dict:
                deck_vector.append(deck_dict[cardstorm_id])
            else:
                deck_vector.append(0)

        deck_vector = np.array(deck_vector)

        return deck_vector

    def _deck_to_dict(self, raw_deck_list):
        '''
        Turns a raw deck list into a dictionary, with cardstorm ids as keys and
        card counts as values

        INPUT:
            - raw_deck_list: string, plaintext deck list with cardstrings
                              separated by newlines
        OUTPUT:
            - deck_dict: dictionary, cardstorm ids as keys and card counts as values
        '''

        deck_dict = {}
        for card_string in raw_deck_list.split('\n'):
            if card_string.lower().startswith('sideboard'):
                # we found the sideboard, ignore everything past this line
                break
            if not card_string:
                # we found an empty line, ignore everything past this line
                break
            parse_status, card_name, card_count = parse_card_string(card_string)
            try:
                cardstorm_id = self.card_dict[card_name.lower()]
            except KeyError:
                print('\tcard "{}" not found'.format(card_name))
            deck_dict[cardstorm_id] = int(card_count)

        return deck_dict
