
import sys
import json
import re
import copy




def TextLines(filename):
	file = open(filename)
	
	while True:
		line = file.readline()
		if not line:
			break

		yield line

	file.close()


def SplitFirstHyphen(word):
	pair = tuple()

	match = re.search('-', word)
	if match:
		pair = (word[ : match.start()], word[match.start() + 1 : ])

	return pair

product_name_array = ['manufacturer', 'model', 'family']
product_name_index_manufacturer = 0
product_name_index_model        = 1
product_name_index_family       = 2

# This array describes the strings that we're looking for, built by what we know of the products...
# I could have made this out of naked strings rather than do all this indirection but
# then typos would occur at runtime rather than being safely caught at compile time...
product_name_patterns = [
	[product_name_index_manufacturer, product_name_index_family, product_name_index_model],
	[product_name_index_manufacturer, product_name_index_model],
	[product_name_index_family      , product_name_index_model],
]

# I'm interested to know if any string parsings will result in ambiguous product resolution...
product_ambiguities = {}

# This class recursively matches a list of words to a product.
# It does so one word at a time; a distinct instance of this class for each word.
# For a large database, this would likely be implemented with a proper SQL database.
# However, my priority here is ease of execution so it's implemented as a Python data structure.
# This will likely be significantly faster than a database because of the O(k) execution time of
# Python hashes (dict) instead of the typical O(log(n)) execution time of database table lookups...
class WordListMapper:
	def __init__(self):
		self.word_mappings = {}
		self.product_mapping = []    # this is a list so we may keep track of duplicate mappings...

	def AddMapping(self, product, index, word_list):
		if index == len(word_list):
			self.product_mapping.append(product)

			# If there's a product ambiguity, make note of it...
			if len(self.product_mapping) > 1:
				title = ' '.join(word_list)
				product_ambiguities[title] = [i['product_name'] for i in self.product_mapping]
		else:
			hyphen_pair = SplitFirstHyphen(word_list[index])
			if hyphen_pair:
				# This block will build the equivalence between hyphens, spaces and no space.
				# eg 'cyber-shot', 'cyber shot' and 'cybershot' will resolve to the same product...

				tail = word_list[index + 1 : ]

				# This is the hyphen/space equivalence...
				new_list = list(hyphen_pair)
				new_list.extend(tail)
				self.AddMapping(product, 0, new_list)

				# This is the hyphen/no space equivalence...
				new_list = [''.join(hyphen_pair)]
				new_list.extend(tail)
				self.AddMapping(product, 0, new_list)
			else:
				mapper = self.word_mappings.setdefault(word_list[index], WordListMapper())
				mapper.AddMapping(product, index + 1, word_list)

	def Map(self, word_list, index = 0):
		mapping = tuple()

		if self.word_mappings:
			mapper = self.word_mappings.get(word_list[index])
			if mapper:
				mapping = mapper.Map(word_list, index + 1)
		else:
			mapping = tuple(self.product_mapping)    # don't return our private list...

		return mapping


# Build product string mappings to be used for parsing...

product_title_mapper = WordListMapper()

products_filename = sys.argv[1]
for line in TextLines(products_filename):
	product = json.loads(line)

	for index_pattern in product_name_patterns:
		try:
			word_list = re.split('[\s]+', str.join(' ', (name.strip() for name in (product[product_name_array[index]] for index in index_pattern))).lower())
			product_title_mapper.AddMapping(product, 0, word_list)
		except KeyError:
			pass    # if there's a key error, this pattern doesn't apply and we may safely continue...


# Report any possible product ambiguities for curiosity's sake...
if product_ambiguities:
	log_file = open('ambiguities.txt', 'w')
	for key, values in product_ambiguities.iteritems():
		log_file.write(str(key))
		log_file.write('\n')
		log_file.write(str(values))
		log_file.write('\n')
	log_file.close()


# Parse the collection of product descriptions and look for any products in our product list...

map_collection = {}

count = 0
listings_filename = sys.argv[2]
for line in TextLines(listings_filename):
	listing = json.loads(line)
	listing['lineid'] = count    #  this is not part of the requirements but useful for testing...

	word_list = re.split('[\s-]+', listing['title'].strip().lower())
	product_list = product_title_mapper.Map(word_list)
	if product_list:
		# Make sure there is an unambiguous mapping!
		if len(product_list) == 1:
			result_list = map_collection.setdefault(product_list[0]['product_name'], [])
			result_list.append(listing)
	
	count += 1

# Print our results to stdout...
for name, result_list in map_collection.iteritems():
	output = {'product_name':name, 'listings':[i for i in result_list]}
	print json.dumps(output)




