import SwiftUI
import AlphaDesign
import AlphaData
import AlphaCore

struct FundDiscoverView: View {
    @Binding var searchText: String
    @State private var viewModel = FundSearchViewModel()
    @State private var watchlistViewModel = FundViewModel()
    @State private var showAddedToast = false
    @State private var lastAddedName = ""
    
    var body: some View {
        NavigationStack {
            ZStack {
                LiquidBackground()
                
                List {
                    if searchText.isEmpty {
                        // 热门建议板块
                        Section {
                            VStack(alignment: .leading, spacing: 16) {
                                Text("funds.discover.hot_suggestions")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(.secondary)
                                
                                ScrollView(.horizontal, showsIndicators: false) {
                                    HStack(spacing: 8) {
                                        suggestionChip(title: "博时黄金", code: "159937")
                                        suggestionChip(title: "华安黄金", code: "518880")
                                        suggestionChip(title: "易方达信息", code: "161128")
                                        suggestionChip(title: "沪深300", code: "510300")
                                        suggestionChip(title: "纳指100", code: "513100")
                                    }
                                }
                            }
                            .padding(.vertical, 8)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }
                    
                    if viewModel.isLoading {
                        HStack {
                            Spacer()
                            ProgressView().tint(.blue)
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                    } else if viewModel.results.isEmpty && searchText.count >= 2 {
                        VStack(spacing: 12) {
                            Image(systemName: "doc.text.magnifyingglass")
                                .font(.largeTitle)
                                .foregroundStyle(.gray.opacity(0.3))
                            Text("funds.search.not_found")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                        .listRowBackground(Color.clear)
                    } else {
                        ForEach(viewModel.results) { fund in
                            Button {
                                Task {
                                    await watchlistViewModel.addFund(code: fund.code, name: fund.name)
                                    lastAddedName = fund.name
                                    withAnimation { showAddedToast = true }
                                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                        withAnimation { showAddedToast = false }
                                    }
                                }
                            } label: {
                                HStack {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(fund.name)
                                            .font(.subheadline.bold())
                                            .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                                        HStack {
                                            Text(fund.code).font(.caption2.monospaced())
                                            Text("•").font(.caption2)
                                            Text(fund.company ?? String(localized: "funds.company.unknown")).font(.caption2)
                                        }
                                        .foregroundStyle(.gray)
                                    }
                                    Spacer()
                                    Image(systemName: "plus.circle.fill")
                                        .foregroundStyle(.blue)
                                        .font(.title3)
                                }
                                .padding(.vertical, 4)
                            }
                            .listRowBackground(Color.white.opacity(0.5))
                        }
                    }
                }
                .scrollContentBackground(.hidden)
                // 注意：.searchable 已经在 MainTabView 层级挂载，这里响应 searchText 的变化
                .onChange(of: searchText) {
                    viewModel.query = searchText
                    Task { await viewModel.performSearch() }
                }
                
                // Toast Notification
                if showAddedToast {
                    VStack {
                        Spacer()
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                            Text("\(String(localized: "funds.toast.added_prefix")) \(lastAddedName)")
                        }
                        .font(.system(size: 12, weight: .bold))
                        .padding(.vertical, 12)
                        .padding(.horizontal, 20)
                        .background(.blue)
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                        .shadow(radius: 10)
                        .padding(.bottom, 40)
                    }
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .navigationTitle("funds.discover.title")
        }
    }
    
    private func suggestionChip(title: String, code: String) -> some View {
        Button {
            searchText = code
        } label: {
            Text(title)
                .font(.system(size: 14, weight: .bold))
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
                .foregroundStyle(.blue)
                .glassEffect(.regular, in: .capsule)
                .clipShape(Capsule())
        }
    }
}
