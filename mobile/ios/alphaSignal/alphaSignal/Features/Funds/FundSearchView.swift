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
                
                List {
                    if viewModel.query.isEmpty {
                        // 初始引导空白状态
                        VStack(spacing: 16) {
                            Image(systemName: "text.magnifyingglass")
                                .font(.system(size: 40))
                                .foregroundStyle(.blue.opacity(0.4))
                            Text("search.empty.hint")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding(.vertical, 80)
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    } else if viewModel.isLoading {
                        // 加载状态
                        HStack {
                            Spacer()
                            ProgressView().tint(.blue)
                            Spacer()
                        }
                        .padding(.vertical, 40)
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    } else if viewModel.results.isEmpty && viewModel.query.count >= 2 {
                        // 未找到结果
                        VStack(spacing: 12) {
                            Image(systemName: "magnifyingglass.circle.fill")
                                .font(.system(size: 40))
                                .foregroundStyle(.gray.opacity(0.3))
                            Text("search.empty.no_results")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .center)
                        .padding(.vertical, 80)
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    } else {
                        // 搜索结果列表
                        ForEach(viewModel.results) { fund in
                            Button {
                                onAdd(fund)
                                dismiss()
                            } label: {
                                HStack(spacing: 12) {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(fund.name)
                                            .font(.system(size: 16, weight: .bold))
                                            .foregroundStyle(Color.primary)
                                            .lineLimit(1)
                                        
                                        HStack(spacing: 6) {
                                            Text(fund.code)
                                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                                .foregroundStyle(.secondary)
                                                .padding(.horizontal, 6)
                                                .padding(.vertical, 2)
                                                .background(Color(uiColor: .tertiarySystemFill))
                                                .clipShape(RoundedRectangle(cornerRadius: 6))
                                                
                                            if let type = fund.type, !type.isEmpty {
                                                Text(type)
                                                    .font(.system(size: 10, weight: .semibold))
                                                    .foregroundStyle(.blue)
                                                    .padding(.horizontal, 5)
                                                    .padding(.vertical, 2)
                                                    .background(Color.blue.opacity(0.1))
                                                    .clipShape(RoundedRectangle(cornerRadius: 4))
                                            }
                                            
                                            Text(fund.company ?? String(localized: "funds.company.unknown"))
                                                .font(.system(size: 11))
                                                .foregroundStyle(.gray)
                                        }
                                    }
                                    
                                    Spacer(minLength: 16)
                                    
                                    Image(systemName: "plus.circle.fill")
                                        .font(.system(size: 22))
                                        .foregroundStyle(.blue)
                                        .symbolRenderingMode(.hierarchical)
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal, 4)
                            }
                            .buttonStyle(.plain)
                            .listRowBackground(Color(uiColor: .systemBackground))
                        }
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
            .navigationTitle("search.title")
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $viewModel.query, placement: .navigationBarDrawer(displayMode: .always), prompt: "search.prompt")
            .onChange(of: viewModel.query) { newValue in
                Task { await viewModel.performSearch() }
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("common.cancel") { dismiss() }
                        .foregroundStyle(.primary)
                }
            }
        }
    }
}
