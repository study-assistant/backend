#############################################################################################
# This is a script that will scrape parts of courses from MIT OpenCourseWare.               #
# (https://ocw.mit.edu/)                                                                    #
# We will start from the assumption that every course we download contains at least a main  #
# course page with basic course information and a course calendar (in the form of a table). #
# These are some metadata that we will download for every course and save in JSON format.   #
# For the beginning version, we will dowload only written format of materials as are text,  #
# pdfs or transcripts for video (if available).                                             #
#############################################################################################
from config import LINKS_FILE
from input import read_course_links
from course_pipeline import CoursePipeline
import time

def format_duration(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def banner():
    print("=" * 80)
    print("🎓 MIT OpenCourseWare Scraper")
    print("📚 Downloading course metadata and materials")
    print("=" * 80)
def course_header(index: int, total: int, url: str):
    print("\n" + "-" * 80)
    print(f"▶️  Course {index}/{total}")
    print(f"🔗 {url}")
    print("-" * 80)
def course_footer(course):
    print(f"✅ Finished: {course.title} (Course number: {course.primary_course_number})")
    print("-" * 80)

def main():
    banner()
    pipeline = CoursePipeline()
    links = read_course_links(LINKS_FILE)

    if not links:
        print("⚠️  No course links found. Exiting.")
        return

    total = len(links)
    print(f"📦 Found {total} course(s) to process\n")


    for index, url in enumerate(links, start=1):
        start_time = time.perf_counter()
        try:
            course_header(index, total, url)

            course = pipeline.process_course_main_page(url)
            print(f"📝 Metadata saved for: {course.title}")

            pipeline.process_course_calendar(course)
            print("🗓️  Calendar processed")

            pipeline.process_all_pages(course)
            print("📄 Course pages processed")

            elapsed = time.perf_counter() - start_time
            print(f"\n⏱️  Course finished in {format_duration(elapsed)}")

            course_footer(course)

        except Exception as e:
            print("❌ Error while processing course")
            print(f"   {e}")
            print("➡️  Skipping to next course...\n")

    print("\n🎉 All courses processed!")

if __name__ == "__main__":
    main()