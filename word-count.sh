#!/usr/bin/env bash
cd tex;
for p in *.tex; do
    filename=${p%.*}
    if [[ $filename == "word-count" ]]
    then
       continue
    fi

    (texcount $p -merge -sum | head -n 10 | tail -n +3) > $filename.wordcount 2> /dev/null
    summary=($(grep Sum $filename.wordcount))
    echo ${summary[2]} $'\t' $filename
    printf "%'d words" ${summary[2]} > $filename.wordcountsum

done


for fn in *.wordcount*; do
    if [[ $fn != "thesis.wordcountsum" ]]; then
        rm $fn
    fi
done
