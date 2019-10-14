import pandas as pd
import json


def eclkeyword2df(deck, keyword, debug=False):
    print(debug)
    meta = json.load(open("000_Eclipse100/" + keyword[0] + "/" + keyword))

    if "items" in meta:
        itemsname = "items"
    elif "records" in meta:
        itemsname = "records"
    else:
        pass
        # difficult, PORO is an example

    # 'size' in the meta is the number of records.
    if 'size' not in meta:
        if 'data' in meta:
            meta['size'] = 1
        else:
            meta['size'] = 0

    if 'size' in meta:
        recordcount = meta['size']
        size = None
        if isinstance(recordcount, dict):
            size = deck[recordcount['keyword']][0][recordcount['item']]
        if debug:
            print("recordcount: " + str(size))

    if 'data' in meta:
        # This means that we have a keyword like PORO, or SWOF.
        # Number of data in each record/row can then be huge.
        pass
    elif 'items' in meta:
        # Easier..?
        pass

    columns = [x["name"] for x in meta[itemsname]]
    if debug:
        print("items is called " + str(itemsname))
        print("%d columns" % len(columns))
    rowlist = []
    rowidx = 0
    while True:
        try:
            rowdata = [
                deck[keyword][rowidx][pos][0] for pos in range(len(meta[itemsname]))
            ]
            if debug:
                print("rowdata: " + str(rowdata))
                print("rowidx: " + str(rowidx))
            rowlist.append(rowdata)
            rowidx += 1
        except IndexError:
            break

    return pd.DataFrame(rowlist, columns=columns)
