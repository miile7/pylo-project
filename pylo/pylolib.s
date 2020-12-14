/**
 * Returns whether the `text` contains numbers and optional one dot and optional one minus at the 
 * start only. Note that any added whitespace will return false already.
 *
 * @param text
 *      The text to check
 *
 * @return
 *      Whether the `text` is a valid number expression or not
 */
number pylolib_is_numeric(string text){
    if(text == ""){
        return 0;
    }

    number minus_found = 0;
    number dot_found = 0;

    for(number i = 0; i < text.len(); i++){
        string c = text.mid(i, 1);
        number a = asc(c);

        if((a < 48 || a > 57) && (i != 0 || c != "-") && (dot_found || c != ".")){
            return 0;
        }
    }

    return 1;
}

/**
 * Removes the characters of the `charlist` from the `str` if they are at the start or at the end of
 * the string.
 *
 * @param str
 *		The string to remove the characters from
 * @param charlist?
 *		A string defining the characters that should be removed from the front and from the end,
 *		default: " \n\r\t"
 *
 * @return 
 *      The trimmed string
 */
String pylolib_trim(String str, String charlist){
	// position of the first non-remove character
	number spos = 0;
	// position of the last non-remove character
	number epos = str.len() - 1;
	String c;
	String t;

	// find start position
	for(number i = 0; i < str.len(); i++){
		c = str.mid(i, 1);

		for(number j = 0; j < charlist.len(); j++){
			t = charlist.mid(j, 1);
			
			if(c == t){
				// save the position of the next valid character, this character is in the trim list
				// so it should be removed
				spos = i + 1;
				break;
			}
		}

		if(spos != i + 1){
			// current character is not a trim character
			break;
		}
	}

	// find end position
	for(number i = str.len() - 1; i >= 0; i--){
		c = str.mid(i, 1);

		for(number j = 0; j < charlist.len(); j++){
			t = charlist.mid(j, 1);

			if(c == t){
				// save the position of the next valid character, this character is in the trim list
				// so it should be removed
				epos = i - 1;
				break;
			}
		}

		if(epos != i - 1){
			// current character is not a trim character
			break;
		}
	}

	return str.mid(spos, epos - spos + 1);
}
String pylolib_trim(String str){
	return pylolib_trim(str, " \n\r\t");
}

/**
 * Convert the number `num` to a decimal number for the given `base`.
 *
 * Note that there must not be any prefixes!
 *
 * @param num
 *      The number to convert
 * @param base
 *      The base to use
 * @param parsable
 *      Whether the number was parsable or not
 *
 * @return
 *      The parsed number or 0 if it was not parsable
 */
number pylolib_base2dec(string num, number base, number &parsable){
    num = num.pylolib_trim();

    parsable = 1;
    number dec = 0;
    // whether the number is negative or not
    number n = 0;
    // number maximum
    number nm = min(58, 48 + base);
    // upper case maximum, subtract 10 because starts by A=10
    number um = max(65, 65 + base - 10);
    // lower case maximum, equal to upper case but different ascii codes
    number lm = max(97, 97 + base - 10);
    // the position of the digit to parse, counting from back to front
    number pos = 0;

    for(number i = num.len() - 1; i >= 0; i--){
        string c = num.mid(i, 1);
        number a = c.asc();

        if(i == 0 && c == "-"){
            n = 1;
        }
        else if(48 <= a && a < nm){
            // the current character is a digit and it is allowed for this base
            dec += base**pos * (a - 48);
            pos++;
        }
        else if(65 <= a && a < um){
            // the current character is an upper case letter and it is allowed for this base, add
            // 10 because A=10, ...
            dec += base**pos * (a - 65 + 10);
            pos++;
        }
        else if(97 <= a && a < lm){
            // the current character is an lower case letter and it is allowed for this base, add
            // 10 because a=10, ...
            dec += base**pos * (a - 97 + 10);
            pos++;
        }
        else{
            parsable = 0;
            break;
        }
    }

    if(parsable == 1){
        if(n == 1){
            return -1 * dec;
        }
        else{
            return dec;
        }
    }
    else{
        return 0;
    }
}

/**
 * Convert the given `hex` to a decimal number. This function can also deal with prefixes like 
 * '0x' and '0X'.
 *
 * @param hex
 *      The hex number to parse
 * @param parsable
 *      Whether the number was parsable or not
 *
 * @return 
 *      The parsed number or 0 if it was not parsable
 */
number pylolib_hex2dec(string hex, number &parsable){
    hex = hex.pylolib_trim();

    if(hex == "" || hex == "0x" || hex == "0X"){
        parsable = 0;
        return 0;
    }

    // temporary remove - sign, otherwise prefix cannot be removed
    string negative = hex.left(1);
    if(negative == "-"){
        hex = hex.right(hex.len() - 1);
    }

    // remove 0x prefix
    if(hex.len() >= 2){
        string prefix = hex.left(2);
        if(prefix == "0x" || prefix == "0X"){
            hex = hex.right(hex.len() - 2);
        }
    }

    // add negative sign again
    if(negative == "-"){
        hex = negative + hex;
    }

    return pylolib_base2dec(hex, 16, parsable)
}

/**
 * Removes the entry with the given `index` from the choice `container`.
 *
 * @param container
 *      The dialog choice
 * @param index
 *      The index
 *
 * @return 
 *      The choice container
 */
TagGroup pylolib_DLGRemoveChoiceItemEntry(TagGroup container, number index){
    TagGroup items;
    container.TagGroupGetTagAsTagGroup("Items", items);
    items.TagGroupDeleteTagWithIndex(index);
    container.TagGroupSetTagAsTagGroup("Items", items);

    return container;
}

/**
 * Removes the entry with the given `label` from the choice `container`.
 *
 * @param container
 *      The dialog choice
 * @param label
 *      The label of the choice item
 *
 * @return 
 *      The choice container
 */
TagGroup pylolib_DLGRemoveChoiceItemEntry(TagGroup container, string label){
    TagGroup items;
    container.TagGroupGetTagAsTagGroup("Items", items);

    for(number i = 0; i < items.TagGroupCountTags(); i++){
        TagGroup item;
        items.TagGroupGetIndexedTagAsTagGroup(i, item);

        string l;
        item.TagGroupGetTagAsString("Label", l);

        if(l == label){
            items.TagGroupDeleteTagWithIndex(i);
            break;
        }
    }

    container.TagGroupSetTagAsTagGroup("Items", items);

    return container;
}