//
//  Item.swift
//  alphaSignal
//
//  Created by 草莓凤梨 on 2/8/26.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
