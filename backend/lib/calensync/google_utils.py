def get_recurrent_event_id(original_event_id: str, fetched_recurrent_instance_id: str):
    """
    Given an source event part of a recurrence, and the fetched source recurrence, creates
    an id which should correspond to an existing copy of the source event inside the synchronized calendar.
    More generally:

    1. source event 123_20200103 with recurrence source 123
    2. find the recurrence source in the synced calendar (e.g. 321)
    3. generate the event id in the synced calendar, matching 123_20200103 -> 321_20200103

    This function handles step 3 specifically
    """
    if original_event_id.startswith('_'):
        # this happens with events imported from ICalendars. We need to skip the initial underscore
        # so that the rest of the code works as expected. Remember that the second part of the
        # original event id must always be the date of the instance
        original_event_id = original_event_id[1:]

    if "_" in fetched_recurrent_instance_id:
        # for events with _R, you don't want to try and delete id_R{date}_{date},
        # so we re-write the event correctly
        final_id = f'{fetched_recurrent_instance_id.split("_")[0]}_{original_event_id.split("_")[1]}'
    else:
        final_id = f'{fetched_recurrent_instance_id}_{original_event_id.split("_")[1]}'

    return final_id
