from workspace import RAW_DATA_DIR
from workspace import validate_raw_data_directory, create_preprocessing_workspace
from course_processor import process_course

def run():
    validate_raw_data_directory()
    create_preprocessing_workspace()

    course_dirs = [
        path for path in RAW_DATA_DIR.iterdir()
        if path.is_dir()
    ]

    print(f"📦 Found {len(course_dirs)} course(s) to process\n")
    print("-" * 80)

    for course_dir in course_dirs:
        print(f"\n📚 Processing course: {course_dir.name}")
        
        process_course(course_dir)
        
        print(f"\n✅ Processed course: {course_dir.name}")
        print("-" * 80)

if __name__ == "__main__":
    run()