def compare_university_data(old_data, new_data):
    """
    Возвращает словарь изменений {inn: описание изменений}
    """
    changes = {}
    for inn, new_row in new_data.items():
        old_row = old_data.get(inn)
        if not old_row:
            changes[inn] = "Появились новые данные."
            continue

        diffs = []
        for key in ['exam_date', 'application_status']:
            if old_row.get(key) != new_row.get(key):
                diffs.append(f"{key} изменился с '{old_row.get(key)}' на '{new_row.get(key)}'")

        if diffs:
            changes[inn] = "; ".join(diffs)
    return changes
