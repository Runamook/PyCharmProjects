def unique_list(inlist, sub_id):

    if sub_id in inlist:
        return inlist

    elif sub_id not in inlist:
        inlist.append(sub_id)
        return inlist
