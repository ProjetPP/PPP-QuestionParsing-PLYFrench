echo "Il est midi." | /usr/lib/jvm/java-8-openjdk-amd64/bin/java -mx300m -classpath stanford-postagger-full-2014-10-26/stanford-postagger.jar edu.stanford.nlp.tagger.maxent.MaxentTagger -model stanford-postagger-full-2014-10-26/models/french.tagger -textFile /dev/stdin 2> /dev/null

