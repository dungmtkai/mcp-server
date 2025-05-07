import requests
import json

def check_availability(branch: str, date: str, time: str):
    """Check available time slots for a specific branch and date.
    Args:
            time (Optional[str]): The time of the appointment in 'HH:MM' format (e.g., 14:30). Must be between 08:00 and 20:00
            branch (Optional[str]): The name of the salon branch
            date (Optional[str]): The date of the appointment in DD-MM_YYYY format
    """

    # Get salon id
    url = f"https://storage.30shine.com/web/v3/configs/get_all_salon.json?"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = json.loads(response.content.decode('utf-8-sig'))
        all_salon = data["data"]
        id_salon = None
        for salon in all_salon:
            if salon["addressNew"] == branch:
                id_salon = salon["id"]
                break

        # Check available slot
        check_slot_url = f"https://3sgus10dig.execute-api.ap-southeast-1.amazonaws.com/Prod/booking-view-service/api/v1/booking/book-hours-group?salonId={id_salon}&bookDate={date}&timeRequest={time}"

        try:
            response_slot = requests.get(check_slot_url, timeout=5)
            response_slot.raise_for_status()
            data_slot = json.loads(response_slot.content.decode('utf-8-sig'))
            list_hours = data_slot["data"]["hourGroup"]

            # Tách phần giờ và phút từ chuỗi thời gian
            hour, minute = time.split(':')  # Lấy giờ và phút
            # Định dạng lại ngày giờ
            hour = hour.lstrip("0")
            if int(minute) % 20 != 0:
                convert_minute = (int(minute) // 20) * 20
                if convert_minute == 0:
                    minute = str(convert_minute) + "0"
                else:
                    minute = str((int(minute) // 20) * 20)

            hour_minute = f"{hour}h{minute}"  # Định dạng giờ phút theo chuẩn

            # Tìm nhóm giờ hiện tại
            find_hour_group = next(
                (hourGroup for hourGroup in list_hours if hourGroup['name'] == hour),
                None
            )

            # Kết quả trả về
            return_response= {"isFree": False, "hourId": "", "subHourId": "", "nearest_free_before": None,
                        "nearest_free_after": None}

            if find_hour_group:
                # Tìm thời gian khớp trong nhóm giờ hiện tại
                time_matching = next(
                    (hour for hour in find_hour_group['hours'] if hour['hour'] == hour_minute),
                    None
                )

                # Kiểm tra nếu `time_matching` tồn tại và có `isFree = True`
                if time_matching:
                    return_response["isFree"] = time_matching["isFree"]
                    return_response["hourId"] = time_matching["hourId"]
                    return_response["subHourId"] = time_matching["subHourId"]

                    # Lấy giờ hiện tại
                    current_hour = int(hour)

                    def time_to_minutes(time_str):
                        """
                        Chuyển chuỗi giờ dạng 'hhhmm' thành số phút kể từ 00:00.
                        """
                        hour, minute = map(int, time_str.replace('h', ':').split(':'))
                        return hour * 60 + minute

                    # Hàm tìm giờ gần nhất trống trong danh sách
                    def find_nearest_free(hours, target_hour):
                        target_minutes = time_to_minutes(target_hour)
                        before = after = None
                        for h in hours:
                            if h["isFree"]:
                                current_minutes = time_to_minutes(h["hour"])
                                if current_minutes < target_minutes:
                                    before = h
                                elif current_minutes > target_minutes and after is None:
                                    after = h
                        return before, after

                    # Tìm giờ trống trong phạm vi 1 tiếng liền kề
                    relevant_hour_groups = [
                        group for group in list_hours
                        if current_hour - 4 <= int(group["name"]) <= current_hour + 4
                    ]
                    all_hours = [hour for group in relevant_hour_groups for hour in group["hours"]]
                    nearest_before, nearest_after = find_nearest_free(all_hours, time_matching["hour"])

                    # Gán kết quả giờ gần nhất trước và sau vào response
                    return_response["nearest_free_before_booked_time"] = {
                        "hourFrame": nearest_before["hourFrame"],
                        "hourId": nearest_before["hourId"],
                        "subHourId": nearest_before["subHourId"],
                    } if nearest_before else None

                    return_response["nearest_free_after_booked_time"] = {
                        "hourFrame": nearest_after["hourFrame"],
                        "hourId": nearest_after["hourId"],
                        "subHourId": nearest_after["subHourId"],
                    } if nearest_after else None
            print(return_response)
            return return_response

        except (requests.RequestException, json.JSONDecodeError, KeyError):
            return "Dạ xin lỗi, em không thể cung cấp thông tin này."
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        return "Dạ xin lỗi, em không thể cung cấp thông tin này."


if __name__ == "__main__":
    branch = "68 Đình Phong Phú,P. Tăng Nhơn Phú B, Quận 9, TP Thủ Đức"
    date = "09-05-2025"
    time = "09:30"
    check_availability(branch, date, time)