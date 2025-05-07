# tools.py
# MCP tools and prompt for haircut scheduling
from typing import Optional
from mcp.server.fastmcp import FastMCP
import requests
import json
from config import BRANCH_HOURS, CITY_IDS
from utils import generate_time_slots, euclidean_distance

# Initialize appointments list
appointments = []

def init_mcp() -> FastMCP:
    """Initialize FastMCP server."""
    return FastMCP("haircut_scheduler")

mcp = init_mcp()

@mcp.prompt(name="collect_booking_info", description="Thu thập thông tin đặt lịch cắt tóc")
def collect_booking_info(
    user_address: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    phone: Optional[str] = None
) -> list[str]:
    """Collect missing booking information from the user."""
    messages = []
    if not user_address:
        messages.append(
            "Dạ, hệ thống bên em có hơn 100 chi nhánh trên khắp cả nước, như Hà Nội, Hồ Chí Minh, Hải Phòng, Bình Dương, Vinh, Đồng Nai... Anh ở khu vực nào để em giúp tìm salon gần nhất"
        )
    if not date:
        messages.append("Bạn muốn đặt lịch vào ngày nào? (Định dạng: YYYY-MM-DD)")
    if not time:
        messages.append("Bạn muốn đặt lịch vào khung giờ nào? (Định dạng: HH:MM, từ 08:00 đến 20:00)")
    if not phone:
        messages.append("Vui lòng cung cấp số điện thoại của bạn để xác nhận lịch hẹn.")
    return messages

@mcp.tool()
def list_branches() -> str:
    """List available salon branches."""
    url = "https://storage.30shine.com/web/v3/configs/get_all_salon.json"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = json.loads(response.content.decode('utf-8-sig'))
        return (
            f"Hiện tại bên em đang có {int(data['count'])} chi nhánh khác nhau trên khắp cả nước như "
            "Hà Nội, Hồ Chí Minh, Hải Phòng, Bình Dương, Vinh, Đồng Nai. "
            "Anh ở khu vực nào để em giúp tìm salon gần nhất?"
        )
    except (requests.RequestException, json.JSONDecodeError):
        return "Dạ xin lỗi, em không thể cung cấp thông tin này."

@mcp.tool()
def get_near_salon(user_address: str, city: str) -> str:
    """Suggest the nearest salon based on user address and city.
    Args:
        user_address (str): The street address or specific location provided by the user
        city (str): The city name where the user is located
    """
    url = f"https://geocode.search.hereapi.com/v1/geocode?q={user_address}+{city}&apiKey=A7V_JCsxV2Y_A_WBg00q_mUB-bDCynwEhwaZeT6QfwY&limit=1"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = json.loads(response.content.decode('utf-8-sig'))
        res = data["items"][0]
        city_id = CITY_IDS.get(res['address']['county'])
        if city_id is None:
            return "Không tìm thấy thành phố phù hợp. Vui lòng thử lại."

        lat_lon = res['position']
        near_salon = {'city_id': city_id, 'lat': lat_lon['lat'], 'lon': lat_lon['lng']}

        url_get_all_salon = "https://storage.30shine.com/web/v3/configs/get_all_salon.json"
        response = requests.get(url_get_all_salon, timeout=5)
        response.raise_for_status()
        data = json.loads(response.content.decode('utf-8-sig'))

        salons = [x for x in data["data"] if x["cityId"] == near_salon['city_id']]
        salons.sort(
            key=lambda x: euclidean_distance(
                near_salon['lat'], near_salon['lon'], x['latitude'], x['longitude']
            )
        )

        if not salons:
            return "Không tìm thấy salon nào gần khu vực của bạn."

        list_salon = "Danh sách salon\n" + "\n".join(
            f"- **{x['addressNew']}**" for x in salons[:5]
        )
        return list_salon
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        return "Dạ xin lỗi, em không thể cung cấp thông tin này."

@mcp.tool()
def check_availability(branch: str, date: str, time: str) -> list[str]:
    """Check available time slots for a specific branch and date."""
    if branch not in BRANCH_HOURS:
        return [f"Không tìm thấy thông tin cho chi nhánh {branch}."]

    hours = BRANCH_HOURS[branch]
    all_slots = generate_time_slots(hours["start"], hours["end"], hours["interval"])
    booked_slots = [
        appt["time"] for appt in appointments
        if appt["branch"] == branch and appt["date"] == date
    ]
    return [slot for slot in all_slots if slot not in booked_slots]

@mcp.tool()
async def book_appointment(
    time: Optional[str] = None,
    branch: Optional[str] = None,
    date: Optional[str] = None,
    phone: Optional[str] = None
) -> str:
    """Book a haircut appointment.
        Args:
            time (Optional[str]): The time of the appointment in 'HH:MM' format (e.g., "14:30"). Must be between 08:00 and 20:00
            branch (Optional[str]): The name of the salon branch (e.g., "Cơ sở Hà Nội").
            date (Optional[str]): The date of the appointment in 'YYYY-MM-DD' format (e.g., "2025-05-10").
            phone (Optional[str]): The user's phone number for confirming the appointment.
    """
    if not all([branch, date, time, phone]):
        result = await mcp.get_prompt(
            "collect_booking_info",
            {"branch": branch, "date": date, "time": time, "phone": phone}
        )
        texts = [msg.content if isinstance(msg.content, str) else msg.content.text
                 for msg in result.messages]
        return "\n".join(texts)

    try:
        hour = int(time.split(":")[0])
        if hour < 8 or hour > 20:
            return "Giờ đặt không hợp lệ. Vui lòng chọn khung giờ từ 08:00 đến 20:00."
    except ValueError:
        return "Định dạng giờ không hợp lệ. Vui lòng sử dụng định dạng HH:MM."

    for appt in appointments:
        if appt["branch"] == branch and appt["date"] == date and appt["time"] == time:
            return "Khung giờ này đã được đặt. Vui lòng chọn khung giờ khác."

    appointments.append({
        "branch": branch,
        "date": date,
        "time": time,
        "phone": phone
    })
    return f"Đã đặt lịch thành công tại {branch} vào {date} lúc {time} cho số điện thoại {phone}."

@mcp.tool()
def cancel_appointment(phone: str) -> str:
    """Cancel an appointment based on phone number."""
    global appointments
    initial_count = len(appointments)
    appointments = [appt for appt in appointments if appt["phone"] != phone]
    if len(appointments) < initial_count:
        return f"Đã hủy lịch hẹn cho số điện thoại {phone}."
    return f"Không tìm thấy lịch hẹn cho số điện thoại {phone}."