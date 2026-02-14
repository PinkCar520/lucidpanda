import SwiftUI
import AlphaDesign
import AlphaData

struct FundSearchView: View {
    @State private var viewModel = FundSearchViewModel()
    @Environment(\.dismiss) var dismiss
    var onAdd: (FundSearchResult) -> Void
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                VStack(spacing: 0) {
                    // 搜索输入
                    HStack {
                        Image(systemName: "magnifyingglass").foregroundStyle(.blue)
                        TextField("输入基金代码或名称...", text: $viewModel.query)
                            .textFieldStyle(.plain)
                            .onChange(of: viewModel.query) {
                                Task { await viewModel.performSearch() }
                            }
                        if !viewModel.query.isEmpty {
                            Button { viewModel.query = "" } label: {
                                Image(systemName: "xmark.circle.fill").foregroundStyle(.gray)
                            }
                        }
                    }
                    .padding()
                    .background(Color.black.opacity(0.03))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding()
                    
                    List {
                        if viewModel.isLoading {
                            HStack {
                                Spacer()
                                ProgressView().tint(.blue)
                                Spacer()
                            }
                            .listRowBackground(Color.clear)
                        } else if viewModel.results.isEmpty && viewModel.query.count >= 2 {
                            Text("未找到相关基金")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .listRowBackground(Color.clear)
                        } else {
                            ForEach(viewModel.results) { fund in
                                Button {
                                    onAdd(fund)
                                    dismiss()
                                } label: {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(fund.name)
                                            .font(.subheadline.bold())
                                            .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                                        HStack {
                                            Text(fund.code).font(.caption2.monospaced())
                                            Text("•").font(.caption2)
                                            Text(fund.company ?? "未知机构").font(.caption2)
                                        }
                                        .foregroundStyle(.gray)
                                    }
                                    .padding(.vertical, 4)
                                }
                                .listRowBackground(Color.white.opacity(0.5))
                            }
                        }
                    }
                    .scrollContentBackground(.hidden)
                }
            }
            .navigationTitle("查找 Alpha 基金")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("关闭") { dismiss() }
                }
            }
        }
    }
}
