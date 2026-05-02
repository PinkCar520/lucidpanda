import SwiftUI
import AlphaCore
import AlphaData
import OSLog

@Observable
class ProfileEditViewModel {
    private let logger = AppLog.root
    var profileName: String = ""
    var profileNickname: String = ""
    var profileGender: String = ""
    var profileBirthday: Date = Date()
    var profileHasBirthday: Bool = false
    var profileLocation: String = ""
    var isProfileSaving: Bool = false
    var profileSaveSuccess: Bool = false
    var profileSaveError: String? = nil

    private let userProfile: UserProfileDTO?

    init(userProfile: UserProfileDTO?) {
        self.userProfile = userProfile
        if let profile = userProfile {
            self.profileNickname = profile.nickname ?? ""
            self.profileGender = profile.gender ?? ""
        }
    }

    @MainActor
    func saveProfile(appLanguage: String, rootViewModel: AppRootViewModel) async {
        isProfileSaving = true
        defer { isProfileSaving = false }

        struct ProfileUpdatePayload: Encodable {
            var name: String?
            var nickname: String?
            var gender: String?
            var birthday: String?
            var languagePreference: String?

            enum CodingKeys: String, CodingKey {
                case name, nickname, gender, birthday
                case languagePreference = "language_preference"
            }
        }

        let birthdayStr: String?
        if profileHasBirthday {
            let fmt = DateFormatter()
            fmt.dateFormat = "yyyy-MM-dd"
            birthdayStr = fmt.string(from: profileBirthday)
        } else {
            birthdayStr = nil
        }

        let langToSave = appLanguage == "system" ? nil : appLanguage

        let payload = ProfileUpdatePayload(
            name: profileName.isEmpty ? nil : profileName,
            nickname: profileNickname.isEmpty ? nil : profileNickname,
            gender: profileGender.isEmpty ? nil : profileGender,
            birthday: birthdayStr,
            languagePreference: langToSave
        )

        do {
            let _: UserProfileDTO = try await APIClient.shared.send(
                path: "/api/v1/auth/me",
                method: "PATCH",
                body: payload
            )
            await rootViewModel.fetchUserProfile()
            profileSaveSuccess = true
        } catch {
            profileSaveError = error.localizedDescription
        }
    }
}

struct ProfileEditView: View {
    @State private var viewModel: ProfileEditViewModel
    @Environment(AppRootViewModel.self) private var rootViewModel
    @AppStorage("appLanguage") private var appLanguage: String = "system"
    @AppStorage("appAppearance") private var appAppearance: String = "system"
    @Environment(\.dismiss) var dismiss

    init(userProfile: UserProfileDTO?) {
        _viewModel = State(initialValue: ProfileEditViewModel(userProfile: userProfile))
    }

    var body: some View {
        @Bindable var bindable = viewModel
        ZStack {
            Color.Alpha.background.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 24) {
                    VStack(spacing: 0) {
                        SettingsSectionHeader(title: "settings.section.basic_info")
                        PremiumCard {
                            VStack(spacing: 0) {
                                settingsValueRow(label: "settings.field.email", value: rootViewModel.userProfile?.email ?? "—", showDivider: true)
                                
                                HStack(spacing: 16) {
                                    Text(LocalizedStringKey("settings.field.nickname"))
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(Color.Alpha.textPrimary)
                                        .frame(width: 80, alignment: .leading)
                                    
                                    TextField(LocalizedStringKey("settings.field.nickname.placeholder"), text: $bindable.profileNickname)
                                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                                        .multilineTextAlignment(.trailing)
                                        .foregroundStyle(Color.Alpha.taupe)
                                }
                                .padding(.vertical, 14)
                                .padding(.horizontal, 16)
                            }
                        }
                    }

                    VStack(spacing: 0) {
                        SettingsSectionHeader(title: "settings.section.preferences")
                        PremiumCard {
                            VStack(spacing: 0) {
                                HStack(spacing: 16) {
                                    Text(LocalizedStringKey("settings.item.language"))
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(Color.Alpha.textPrimary)
                                    Spacer()
                                    Picker("", selection: $appLanguage) {
                                        Text("settings.language.system").tag("system")
                                        Text("settings.language.en").tag("en")
                                        Text("settings.language.zh").tag("zh-Hans")
                                    }
                                    .pickerStyle(.menu)
                                    .labelsHidden()
                                    .tint(Color.Alpha.brand)
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal, 16)
                                
                                Divider()
                                    .background(Color.Alpha.separator)
                                    .padding(.leading, 16)
                                
                                HStack(spacing: 16) {
                                    Text(LocalizedStringKey("settings.item.appearance"))
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundStyle(Color.Alpha.textPrimary)
                                    Spacer()
                                    Picker("", selection: $appAppearance) {
                                        Text("common.system").tag("system")
                                        Text("common.light").tag("light")
                                        Text("common.dark").tag("dark")
                                    }
                                    .pickerStyle(.menu)
                                    .labelsHidden()
                                    .tint(Color.Alpha.brand)
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal, 16)
                            }
                        }
                    }

                    VStack(spacing: 0) {
                        SettingsSectionHeader(title: "settings.field.gender")
                        PremiumCard {
                            HStack(spacing: 16) {
                                Text(LocalizedStringKey("settings.field.gender"))
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(Color.Alpha.textPrimary)
                                Spacer()
                                Picker("", selection: $bindable.profileGender) {
                                    Text(LocalizedStringKey("settings.field.gender.unset")).tag("")
                                    Text(LocalizedStringKey("settings.field.gender.male")).tag("male")
                                    Text(LocalizedStringKey("settings.field.gender.female")).tag("female")
                                }
                                .pickerStyle(.menu)
                                .labelsHidden()
                                .tint(Color.Alpha.brand)
                            }
                            .padding(.vertical, 8)
                            .padding(.horizontal, 16)
                        }
                    }
                }
                .padding(.top, 16)
                .padding(.bottom, 32)
            }
        }
        .navigationTitle(LocalizedStringKey("settings.section.basic_info"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await viewModel.saveProfile(appLanguage: appLanguage, rootViewModel: rootViewModel) }
                } label: {
                    if viewModel.isProfileSaving {
                        ProgressView().scaleEffect(0.8)
                    } else {
                        Image(systemName: "checkmark")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Color.Alpha.brand)
                    }
                }
                .disabled(viewModel.isProfileSaving)
            }
        }
        .alert("common.success", isPresented: $bindable.profileSaveSuccess) {
            Button("common.ok", role: .cancel) {}
        } message: {
            Text("settings.profile.save_success")
        }
        .alert("common.error", isPresented: Binding(
            get: { viewModel.profileSaveError != nil },
            set: { if !$0 { viewModel.profileSaveError = nil } }
        )) {
            Button("common.ok", role: .cancel) {}
        } message: {
            Text(viewModel.profileSaveError ?? "")
        }
    }

    private func settingsValueRow(label: LocalizedStringKey, value: String, showDivider: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 16) {
                Text(label)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Color.Alpha.textPrimary)
                    .frame(width: 80, alignment: .leading)
                
                Spacer()
                
                Text(value)
                    .font(.system(size: 14, weight: .medium, design: .monospaced))
                    .foregroundStyle(Color.Alpha.taupe)
                    .lineLimit(1)
            }
            .padding(.vertical, 14)
            .padding(.horizontal, 16)
            
            if showDivider {
                Divider()
                    .background(Color.Alpha.separator)
                    .padding(.leading, 16)
            }
        }
    }
}
