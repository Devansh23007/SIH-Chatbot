from services.rag_service import search_careers


question = "I enjoy working with Excel, numbers and analyzing data."

print("Student question:")
print(question)

print("\nSearching career knowledge base...\n")

results = search_careers(question)

for result in results:
    print(
        f"{result['career']}: "
        f"{result['similarity']:.4f}"
    )