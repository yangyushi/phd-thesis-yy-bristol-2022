#!/usr/bin/env python
import re
import sys
from textwrap import dedent

STOPWORDS = [  # common stop words from package nltk
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "you're", "you've", "you'll",
    "you'd", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "she's",
    "her", "hers", "herself", "it", "it's", "its", "itself", "they", "them", "their", "theirs",
    "themselves", "what", "which", "who", "whom", "this", "that", "that'll", "these", "those", "am",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while",
    "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "don't", "should",
    "should've", "now", "d", "ll", "m", "o", "re", "ve", "y", "ain", "aren", "aren't", "couldn",
    "couldn't", "didn", "didn't", "doesn", "doesn't", "hadn", "hadn't", "hasn", "hasn't", "haven",
    "haven't", "isn", "isn't", "ma", "mightn", "mightn't", "mustn", "mustn't", "needn", "needn't",
    "shan", "shan't", "shouldn", "shouldn't", "wasn", "wasn't", "weren", "weren't", "won", "won't",
    "wouldn", "wouldn't"
]


def detect_entry(i, content):
    """
    Determine if a bib entry starts at position i
    """
    end = 0
    for idx in range(i, len(content)):
        if content[idx] == "\n":
            end = idx
            break
    return re.match(r"@\w+{.+", content[i:end]) is not None


def parse_file(bib_content):
    cursor = 0
    stack = []
    in_entry = False
    in_content = False
    for i, letter in enumerate(bib_content):
        if letter == "@":
            if detect_entry(i, bib_content):
                cursor = i
                in_entry = True
        if (letter == '{') and in_entry:
            stack.append(1)
            in_content = True
        if (letter == '}') and in_content:
            stack.pop()
        if in_content and (not stack):
            in_entry = False
            in_content = False
            yield bib_content[cursor:i+1]


def parse_entry(entry):
    entry_pattern = re.compile(
            r'@(\w+){([\W\w]+)}', re.S
    )
    article_type, content = entry_pattern.match(entry).group(1, 2)
    return article_type, content


def get_citekey(content):
    return content.split(',\n')[0]


def remove_annote(content):
    p = re.compile(',\nannote = {.*}', re.DOTALL)
    result = p.search(content)
    if result:
        return content.replace(result.group(), "")
    else:
        return content


def get_author(content):
    fetch = re.search('author = {(.+)}', content)
    if fetch:
        authors = fetch.group(1)
    else:
        authors = 'anonymous'
    first_author = authors.split(',')[0]
    result = re.sub(r'[\\{}]', '', first_author)  # remove modifier such as \v and \c
    result = re.sub(r'\\v', '', first_author)  # remove modifier such as \v and \c
    result = re.sub(r'\\c', '', first_author)  # remove modifier such as \v and \c
    result = re.sub('\W+', '', result).lower()  # remove non ASCII characters
    return result


def get_year(content):
    # year = {YEAR}
    fetch = re.search('year = {(\d+)}', content)
    if fetch:
        return fetch.group(1)
    # date = {YEAR*}
    fetch = re.search('date = {(\d+)\D*.*}', content)
    if fetch:
        return fetch.group(1)
    return ''


def get_journal(content):
    if 'journal' not in content:
        return 'notpaper'
    else:
        for keyname in ["journal", "journaltitle"]:
            search = re.search(r'%s = {(.+)}' % keyname, content)
            if search:
                journal = search.group(1)
                words = [word.lower() for word in journal.split(' ') if re.match('\w+', word)]
                words = [word[0] for word in words if word not in STOPWORDS]
                abbr = ''.join(words)
                if len(abbr) > 1:
                    return abbr
                else:
                    return journal.lower()
        return ""


def reformat_citekey(content, mode='ay', suffix=''):
    year = get_year(content)
    author = get_author(content)
    if mode == 'ay':  # author-year
        citekey = author + year
    elif mode == 'ayj':
        journal = get_journal(content)
        citekey = author + year + journal
    citekey += suffix
    return citekey, re.sub(get_citekey(content), citekey, content)


if __name__ == "__main__":
    help_msg = dedent("""
               usage: ./reform.py input_bib [output_bib]
               (if output_bib not provided, overwriting input_bib)
               """)

    if len(sys.argv) not in [2, 3]:
        print(help_msg)
        exit()

    elif len(sys.argv) == 2:
        if sys.argv[1] in ["-h", "h", "--help", "help"]:
            print(help_msg)
            exit()
        else:
            filename = sys.argv[1]
            new_filename = sys.argv[1]
    else:
        filename = sys.argv[1]
        new_filename = sys.argv[2]

    with open(filename, 'r') as f:
        content = f.read()

    entries = {}
    for i, entry in enumerate(parse_file(content)):
        article_type, content = parse_entry(entry)
        trial_key = get_author(content) + get_year(content)
        if trial_key not in entries.keys():
            key, content = reformat_citekey(content, mode='ay')
        else:
            trial_key = get_author(content) + get_year(content) + get_journal(content)
            num, suffix = 0, ''
            while trial_key in entries.keys():
                num += 1
                suffix = str(num)
                trial_key += suffix
            key, content = reformat_citekey(content, mode='ayj', suffix=suffix)
        entries.update({
            key: {
                'article_type': article_type,
                'content': remove_annote(content)
            }
        })

    new_content = ''
    for key in entries:
        new_content += '@%s{%s}\n\n' % (
            entries[key]['article_type'],
            entries[key]['content'],
        )

    print("{} entries processed".format(i+1))

    with open(new_filename, 'w') as f:
        f.write(new_content)
