wget http://nlp.stanford.edu/software/stanford-postagger-full-2014-10-26.zip -c
unzip stanford-postagger-full-2014-10-26.zip
python3 -c "import nltk; nltk.download('wordnet'); nltk.download('omw')"
