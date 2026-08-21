#!/bin/bash


if [ $# -eq 0 ]; then
   cmd=("grep" "[0-9]")
else
   cmd=("$@")
fi

#while read -r line; do
#    output=$("${cmd[@]}" "$line")
#    if [ $? -eq 0 ]; then
#        echo "$output"
#        # break
#    fi
#done

while read -r line; do
  "${cmd[@]}"
   $line > /dev/null 2>&1 || continue
  echo "$line"
done


# Uses eval: ....
# # If argument provided, use it as command
# if [ $# -gt 0 ]; then
#     cmd="$*"
# else
#     cmd=
# fi

# while read -r line; do
#     output=$(eval "$cmd" "$line")
#     if [ $? -eq 0 ]; then
#         echo "$output"
#         break
#     fi
# done