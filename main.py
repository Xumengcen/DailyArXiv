import sys
import time
import pytz
from datetime import datetime

from utils import get_daily_papers_by_keyword_with_retries, generate_table, back_up_files,\
    restore_files, remove_backups, get_daily_date


beijing_timezone = pytz.timezone('Asia/Shanghai')

# get current beijing time date
current_date_str = datetime.now(beijing_timezone).strftime("%Y-%m-%d")
current_date_obj = datetime.now(beijing_timezone).date() # 转换为 date 对象以便计算

# get last update date from README.md
last_update_date_str = None
try:
    with open("README.md", "r") as f:
        while True:
            line = f.readline()
            if not line: break # 防止文件读完还没找到
            if "Last update:" in line:
                last_update_date_str = line.split(": ")[1].strip()
                break
except FileNotFoundError:
    # 如果是第一次运行，README可能不存在，视为需要更新
    last_update_date_str = None

if last_update_date_str:
    try:
        # 解析上次更新的日期字符串
        last_update_date_obj = datetime.strptime(last_update_date_str, "%Y-%m-%d").date()
        
        # 计算相差天数
        days_diff = (current_date_obj - last_update_date_obj).days
        
        # 【核心修改】如果相差天数小于 3 天，则跳过本次执行
        if days_diff < 3:
            print(f"Last update was on {last_update_date_str}. Only {days_diff} days passed. Skipping update (runs every 3 days).")
            # 注意：此时还没有调用 back_up_files()，所以不需要 restore_files()
            # 但为了保险起见，如果前面有临时文件操作，可以在这里处理。
            # 在当前逻辑流中，直接退出即可，因为备份是在后面才做的。
            sys.exit(0) 
    except ValueError:
        print("Error parsing last update date. Proceeding with update just in case.")
        # 如果日期格式解析失败，为了安全起见，继续执行更新

keywords = ["Composed Video Retrieval", "Composed Image Retrieval", "Multimodal Retrieval"] # TODO add more keywords

max_result = 50 # maximum query results from arXiv API for each keyword
issues_result = 15 # maximum papers to be included in the issue

# all columns: Title, Authors, Abstract, Link, Tags, Comment, Date
# fixed_columns = ["Title", "Link", "Date"]

column_names = ["Title", "Link", "Abstract", "Date", "Comment"]

back_up_files() # back up README.md and ISSUE_TEMPLATE.md

# write to README.md
f_rm = open("README.md", "w") # file for README.md
f_rm.write("# Daily Papers\n")
f_rm.write("The project automatically fetches the latest papers from arXiv based on keywords.\n\nThe subheadings in the README file represent the search keywords.\n\nOnly the most recent articles for each keyword are retained, up to a maximum of 100 papers.\n\nYou can click the 'Watch' button to receive daily email notifications.\n\nLast update: {0}\n\n".format(current_date))

# write to ISSUE_TEMPLATE.md
f_is = open(".github/ISSUE_TEMPLATE.md", "w") # file for ISSUE_TEMPLATE.md
f_is.write("---\n")
f_is.write("title: Latest {0} Papers - {1}\n".format(issues_result, get_daily_date()))
f_is.write("labels: documentation\n")
f_is.write("---\n")
f_is.write("**Please check the [Github](https://github.com/Xumengcen/DailyArXiv) page for a better reading experience and more papers.**\n\n")

for keyword in keywords:
    f_rm.write("## {0}\n".format(keyword))
    f_is.write("## {0}\n".format(keyword))
    if len(keyword.split()) == 1: link = "AND" # for keyword with only one word, We search for papers containing this keyword in both the title and abstract.
    else: link = "OR"
    papers = get_daily_papers_by_keyword_with_retries(keyword, column_names, max_result, link)
    if papers is None: # failed to get papers
        print("Failed to get papers!")
        f_rm.close()
        f_is.close()
        restore_files()
        sys.exit("Failed to get papers!")
    rm_table = generate_table(papers)
    is_table = generate_table(papers[:issues_result], ignore_keys=["Abstract"])
    f_rm.write(rm_table)
    f_rm.write("\n\n")
    f_is.write(is_table)
    f_is.write("\n\n")
    time.sleep(5) # avoid being blocked by arXiv API

f_rm.close()
f_is.close()
remove_backups()
