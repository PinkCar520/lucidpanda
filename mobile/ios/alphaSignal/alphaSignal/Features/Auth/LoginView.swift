import SwiftUI
import AlphaDesign

struct LoginView: View {
    @State private var viewModel = LoginViewModel()
    @Environment(AppRootViewModel.self) private var rootViewModel
    
    var body: some View {
        ZStack {
            LiquidBackground()
            
            VStack(spacing: 40) {
                VStack(spacing: 16) {
                    ZStack {
                        Circle()
                            .fill(Color.blue)
                            .frame(width: 80, height: 80)
                            .shadow(color: .blue.opacity(0.3), radius: 15)
                        
                        Image(systemName: "shield.hexagonpath.fill")
                            .foregroundStyle(.white)
                            .font(.system(size: 40))
                    }
                    
                    Text("AlphaSignal")
                        .font(.system(size: 36, weight: .black, design: .rounded))
                        .foregroundStyle(Color(red: 0.06, green: 0.09, blue: 0.16))
                        .tracking(-1)
                }
                .padding(.top, 60)
                
                LiquidGlassCard {
                    VStack(spacing: 28) {
                        VStack(spacing: 8) {
                            Text("auth.login.title")
                                .font(.system(.caption, design: .monospaced))
                                .fontWeight(.black)
                                .foregroundStyle(.blue)
                                .tracking(4)
                            
                            Text("auth.login.subtitle")
                                .font(.caption2)
                                .foregroundStyle(.black.opacity(0.4))
                        }
                        
                        VStack(spacing: 16) {
                            HStack {
                                Image(systemName: "envelope.fill")
                                    .foregroundStyle(.gray.opacity(0.5))
                                    .frame(width: 24)
                                TextField("auth.field.email", text: $viewModel.email)
                                    .textInputAutocapitalization(.never)
                                    .keyboardType(.emailAddress)
                                    .foregroundStyle(.black)
                            }
                            .padding()
                            .background(Color.black.opacity(0.03))
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                            
                            HStack {
                                Image(systemName: "lock.fill")
                                    .foregroundStyle(.gray.opacity(0.5))
                                    .frame(width: 24)
                                SecureField("auth.field.password", text: $viewModel.password)
                                    .foregroundStyle(.black)
                            }
                            .padding()
                            .background(Color.black.opacity(0.03))
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                        }
                        
                        if let error = viewModel.errorMessage {
                            Text(error)
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(.red)
                        }
                        
                        Button {
                            Task { await viewModel.performLogin() }
                        } label: {
                            HStack {
                                if viewModel.isLoading {
                                    ProgressView().tint(.white)
                                } else {
                                    Text("auth.action.login")
                                        .fontWeight(.black)
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 56)
                            .background(Color.blue)
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                            .shadow(color: .blue.opacity(0.3), radius: 8, y: 4)
                        }
                        .disabled(viewModel.isLoading)
                    }
                }
                .padding(.horizontal, 24)
                
                Spacer()
                
                VStack(spacing: 4) {
                    Text("auth.status.secure_channel")
                    Text("auth.status.module_ready")
                }
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.gray.opacity(0.4))
                .padding(.bottom, 20)
            }
        }
        .onAppear {
            viewModel.onSuccess = {
                rootViewModel.updateState(to: .authenticated)
            }
        }
    }
}
