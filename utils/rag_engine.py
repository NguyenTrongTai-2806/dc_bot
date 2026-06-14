from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from config import GEMINI_API_KEY
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import os

class RAGEngine:
    def __init__(self):
        # 1. Khởi tạo Mô hình Nhúng (Embeddings) - Biến chữ thành số
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # 2. Khởi tạo Mô hình LLM (Gemini 1.5 Flash - Nhanh, thông minh, rẻ)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest", 
            temperature=0.2, # Độ sáng tạo thấp để AI trả lời sát tài liệu, không bịa chuyện
            google_api_key=GEMINI_API_KEY
        )
        
        # 3. Khởi tạo cơ sở dữ liệu Vector DB (Chroma)
        # Giống như SQLite, nó sẽ lưu một thư mục 'chroma_db' vào thư mục 'data/'
        self.persist_directory = "data/chroma_db"
        self.vector_store = Chroma(
            persist_directory=self.persist_directory, 
            embedding_function=self.embeddings
        )
        
        # 4. Công cụ băm nhỏ văn bản
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, # Cắt mỗi đoạn khoảng 1000 ký tự
            chunk_overlap=200 # Cho phép các đoạn gối lên nhau 200 ký tự để không bị đứt ngữ cảnh
        )
        # 5. Bộ nhớ ngắn hạn cho tính năng trò chuyện tự do
        self.chat_memory = {}

    def ingest_document(self, file_path: str) -> int:
        """Đọc file tài liệu, băm nhỏ và lưu vào bộ nhớ (ChromaDB)"""
        # Nhận diện đuôi file để dùng công cụ đọc tương ứng
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            raise ValueError("Định dạng file chưa được hỗ trợ. Chỉ nhận .pdf hoặc .txt")

        # Load và cắt nhỏ tài liệu
        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)
        
        # Mã hóa (nhúng) và lưu vào Vector DB
        self.vector_store.add_documents(chunks)
        return len(chunks)

    def ask(self, question: str) -> str:
        """Nhận câu hỏi, tìm ngữ cảnh trong ChromaDB và ép Gemini trả lời"""
        # Thiết kế tính cách và luật lệ cho AI
        system_prompt = (
            "Bạn là một trợ lý ảo siêu việt của server Discord. "
            "Nhiệm vụ của bạn là trả lời câu hỏi của người dùng dựa HƠN HẾT vào Ngữ cảnh được trích xuất từ tài liệu dưới đây.\n\n"
            "Luật lệ nghiêm ngặt:\n"
            "1. Nếu thông tin không có trong Ngữ cảnh, hãy trả lời: 'Tôi chưa được học thông tin này trong tài liệu'. Tuyệt đối không được tự bịa ra thông tin (hallucination).\n"
            "2. Trả lời ngắn gọn, súc tích, định dạng Markdown đẹp mắt (in đậm, in nghiêng, gạch đầu dòng).\n\n"
            "Ngữ cảnh trích xuất:\n{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        # Thiết lập cơ chế tìm kiếm (lấy 3 đoạn văn bản liên quan nhất tới câu hỏi)
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        
        # Lắp ráp quy trình: Tìm kiếm (Retriever) -> Trộn vào Prompt -> Đưa cho AI (LLM)
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        # Chạy quy trình
        response = rag_chain.invoke({"input": question})
        return response["answer"]

    def clear_memory(self):
        """Xóa sạch trí nhớ (Vector DB)"""
        self.vector_store.delete_collection()
        self.vector_store = Chroma(
            persist_directory=self.persist_directory, 
            embedding_function=self.embeddings
        )

    def chat_freely(self, user_id: str, message: str) -> str:
        """Trò chuyện tự do có trí nhớ theo từng người dùng"""
        system_prompt = (
            "Bạn là một người bạn thân thiết và vui tính trong server Discord này. "
            "Hãy xưng 'mình' và gọi người dùng là 'bạn' hoặc 'mọi người'. "
            "Giọng văn cần tự nhiên, gần gũi, tuyệt đối không được dùng văn phong AI hay thuật ngữ quá phức tạp. "
            "Trả lời ngắn gọn, súc tích và TUYỆT ĐỐI không viết quá dài dòng."
        )

        # Nếu user này mới chat lần đầu, tạo cho họ một cuốn sổ mới ghi sẵn nhân cách của bot
        if user_id not in self.chat_memory:
            self.chat_memory[user_id] = [SystemMessage(content=system_prompt)]

        # Lưu câu hỏi của người dùng vào sổ
        self.chat_memory[user_id].append(HumanMessage(content=message))

        # Giới hạn trí nhớ: Chỉ nhớ cái cốt lõi (index 0) và 10 tin nhắn gần nhất để không tràn RAM và lỗi API
        if len(self.chat_memory[user_id]) > 11:
            self.chat_memory[user_id] = [self.chat_memory[user_id][0]] + self.chat_memory[user_id][-10:]

        # Đưa toàn bộ cuốn sổ cho Gemini đọc và trả lời
        response = self.llm.invoke(self.chat_memory[user_id])
        answer = response.content

        # Lưu lại câu trả lời của AI vào sổ để lần sau nó nhớ là nó đã nói gì
        self.chat_memory[user_id].append(AIMessage(content=answer))
        
        return answer
    
    def reset_user_memory(self, user_id: str):
        """Xóa trí nhớ về một user khi họ muốn chuyển chủ đề hoàn toàn"""
        if user_id in self.chat_memory:
            del self.chat_memory[user_id]
    
    def summarize_text(self, chat_log: str) -> str:
        """Đọc một đoạn lịch sử chat dài và tóm tắt ý chính"""
        system_prompt = (
            "Bạn là một thư ký mẫn cán và vui vẻ của server Discord này. "
            "Nhiệm vụ của bạn là đọc đoạn lịch sử chat dưới đây và tóm tắt lại những ý chính, "
            "chủ đề mọi người đang bàn luận, và các quyết định/công việc cần làm (nếu có). "
            "Hãy trình bày bằng các gạch đầu dòng rõ ràng. Xưng 'mình' và gọi mọi người là 'các bạn'. "
            "Tuyệt đối không bịa thêm thông tin ngoài đoạn chat."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Nội dung lịch sử chat:\n{input}")
        ])

        # Dùng StrOutputParser để ép nó trả về chữ sạch sẽ, không bị lỗi form như vụ chat nữa
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({"input": chat_log})
        
        return response