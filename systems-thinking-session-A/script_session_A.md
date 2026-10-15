# Script thuyết trình: Session A, "Lỗi hết rồi, sao hệ thống vẫn chết?"

Bản này là bản nói đầy đủ, viết gần với lời nói để bạn đọc theo hoặc tự diễn đạt lại. Không có demo. Mốc phút ở mỗi mục tính theo số chữ (khoảng 140 chữ mỗi phút), chưa đo thật. Khi tập, bấm giờ từng phần rồi sửa lại. Thứ tự cắt khi thiếu giờ nằm ở cuối file.

Quy ước: `[ ... ]` là chỉ dẫn sân khấu, không đọc. `(kiểm tra)` là chỗ cần xác nhận lại với nguồn trước khi nói. Ví dụ có ghi "minh họa" là số do mình tự đặt để dễ tính, không phải số đo thật.

---

## Phân công người nói

- **Người 1, khoảng 20 phút:** slide 1 đến 10 (cover, WorkOS, code, lộ trình, Queue, Delay) và slide 22 đến 23 (Bốn điều mang về, cầu sang Session B). Người 1 hỏi câu hỏi đầu buổi nên cũng là người chốt câu trả lời.
- **Người 2, khoảng 20 phút:** slide 11 đến 21 (Catalog, Metastable, vẽ loop, phá loop).
- **Slide 24 (Nguồn tham khảo):** không ai nói, để trên màn hình lúc hỏi đáp.
- **Hỏi đáp:** Người 1 trả lời câu về Queue và Delay, Người 2 trả lời câu về Catalog và Metastable. Câu chung thì ai muốn trả lời cũng được.
- Chỗ bàn giao: sau slide 10 (Người 1 sang Người 2) và sau slide 21 (Người 2 về Người 1). Câu bàn giao nằm ở cuối mục 9, đầu mục 10, cuối mục 17 và đầu mục 18.

---

## 1. Cover (1:00)

**Người nói: Người 1**

Chào mọi người. Mình bắt đầu bằng một cảnh chắc ai làm hệ thống cũng từng gặp. Đêm có sự cố, cả team vào kênh xử lý. Mọi người đào log, tìm ra lỗi, sửa xong, deploy. Rồi ai đó nhìn lại dashboard, và nó vẫn đỏ. Lỗi hết rồi mà hệ thống vẫn chết.

[Dừng một nhịp, chỉ vào tiêu đề.] Đó là câu hỏi của buổi này: cái gì giữ nó lại? Khi nguyên nhân ban đầu đã biến mất, thứ gì vẫn đang giữ hệ thống ở trạng thái hỏng?

Mình sẽ đi qua bốn lớp: hàng đợi, độ trễ, retry, rồi gom lại thành một khái niệm tên là metastable failure. Mỗi lớp mình đều có ví dụ thật. Đây là Session A, phần kỹ thuật. Session B sẽ nhìn cùng loại vòng lặp đó ở phía con người và tổ chức, nên nếu buổi này có chỗ nào nghe quen quen với chuyện team hay chuyện công ty, đó là chủ ý.

## 2. Hook: WorkOS (2:00)

**Người nói: Người 1**

Mình bắt đầu bằng một sự cố thật. Ngày 16/7/2026, WorkOS bị gián đoạn dịch vụ, khoảng từ tám giờ đến mười giờ mười sáng theo giờ UTC, tức là chừng hai tiếng mười phút. Điều lạ là hệ thống không chết hẳn. Nó vẫn chạy, vẫn nhận request, nhưng gần như không request nào hoàn thành.

Nguyên nhân bề mặt: phần lớn connection tới database bị giữ bởi những request đang chờ một connection thứ hai. Tức là request này đang cầm một connection, rồi lại xin thêm một cái nữa, và trong pool không còn cái nào dư. Request timeout thì client retry, retry tạo ra thêm request, họ gọi là request storm. Và họ ghi nhận thêm là borrow timeout, tức thời gian một request được phép đứng chờ lấy connection, đặt quá dài. Nên tình trạng cạn connection bị kéo dài thay vì tự nhả ra.

Có một chi tiết mình muốn nhấn, vì nó là mấu chốt của cả buổi. Theo postmortem, đợt traffic bất thường lúc đó chỉ là trigger, tức cái châm ngòi. Nó không phải root cause. Hệ thống chịu được loại traffic đó ở những lần trước. Nó hỏng vì có một lỗi nằm sẵn trong đường tạo session, mà mình sẽ giải thích ở slide kế. Và vì vậy thêm capacity cũng không cứu được.

Chú ý cách họ viết: một bên là cái làm sự cố bắt đầu, một bên là cái làm sự cố ở lại. Hai thứ đó khác nhau. Postmortem hay dừng ở thứ nhất.

[Chỉ vào thẻ tối bên phải.] Câu hỏi của mình: hệ thống không chết hẳn, vậy cái gì đang giữ nó ở trạng thái chết? Mọi người cứ nghĩ, cuối buổi mình quay lại.

[Nếu có thời gian, hỏi khán phòng: ai từng gặp cảnh "restart xong vẫn không hết" chưa? Để một hai người trả lời, rồi nói tiếp.]

## 2b. Cơ chế: một request giữ hai connection (3:00)

**Người nói: Người 1**

[Slide `hook-code`. Nói trước: đây là code minh họa do mình viết, không phải code của WorkOS.]

Mình dựng lại cơ chế bằng một đoạn pseudocode. Mỗi lần tạo session, hệ thống ghi hai thứ: một event chính, và một event analytics. Người viết code muốn hai lần ghi dùng chung một connection, để hoặc cả hai thành công hoặc cả hai không, nên họ bọc phần ghi analytics trong một nested transaction. Đây là một quyết định rất bình thường, ai viết backend cũng từng làm.

[Chỉ dòng cam, `with db.transaction()`.] Dòng này giữ connection số một.

[Chỉ dòng đỏ, `with tx.nested()`.] Theo postmortem, do một bug của thư viện ORM, nested transaction này lại đi xin connection thứ hai trong khi cái thứ nhất vẫn đang mở. Postmortem không nói tên thư viện, và cũng không nói timeout cụ thể là bao nhiêu, nên mình không đoán. Điểm cần nhớ: không dòng nào trong code của dev trông sai. Lỗi nằm ở chỗ ghép giữa code và thư viện.

Giờ nhìn sang bên phải. Khi tải thấp, mỗi request mượn hai connection, trả lại, và không ai thấy gì. Hệ thống chạy bình thường nhiều tháng như vậy.

Giờ lấy số cho dễ hình dung, đây là số minh họa. Pool có 10 connection. Mười request đến cùng lúc. Mỗi request lấy được một connection, vậy là pool hết chỗ trống. Cả mười request đều đứng đợi connection thứ hai, và không ai nhả cái đang giữ vì còn chờ cái kia. Mỗi người cầm một nửa thứ mình cần và không ai chịu buông. Trong khoa học máy tính cái này có tên riêng, là hold-and-wait, và nó là một trong bốn điều kiện cổ điển của deadlock.

Nhưng nó không phải deadlock đúng nghĩa, vì có timeout. Timeout làm request hỏng, connection được nhả. Vấn đề là ngay sau đó client retry, request xếp hàng lại, và đợt request mới lại cầm connection thứ nhất rồi chờ connection thứ hai. Pool lại cạn. Nên cái timeout, vốn sinh ra để cứu, lại là một phần của vòng lặp.

Đó là chỗ một tải thoáng qua biến thành trạng thái tự duy trì. Lưu ý khi nói: đừng nói WorkOS viết code tệ. Một quyết định hợp lý ở quy mô nhỏ, ghép với một bug ở tầng dưới, gặp tải cao đồng bộ thì thành một vòng lặp. Đó là loại lỗi mà code review không bắt được.

## 3. Roadmap (1:00)

**Người nói: Người 1**

Buổi này có bốn lớp, đi từ nền lên đỉnh, và lớp sau dùng kiến thức của lớp trước. Lớp một là Queue: vì sao hệ thống gần đầy lại mong manh. Lớp hai là Delay: vì sao phản ứng nhanh có thể gây dao động. Lớp ba là Catalog: những họ hàng của retry storm mà mình nhặt từ các postmortem thật. Và lớp cuối là metastable failure, nơi mọi thứ hội tụ. Cái thẻ tối ở cuối slide là cao trào, cũng là câu trả lời cho câu hỏi ở đầu buổi.

Phân công: mình nói nửa đầu, tới hết phần Delay. Từ phần Catalog trở đi Người 2 sẽ nói, rồi mình quay lại để chốt.

## 4. Little's Law (2:30)

**Người nói: Người 1**

Bắt đầu với queue. Có một định luật rất ngắn: L bằng lambda nhân W. L là số request đang ở trong hệ thống, lambda là tốc độ request đến, W là thời gian trung bình mỗi request ở lại.

Ví dụ đời thường trước. Một quán cà phê mỗi phút có hai khách bước vào, mỗi khách ngồi trung bình mười lăm phút. Vậy trung bình trong quán có ba mươi người. Không cần biết ai ngồi bao lâu, không cần biết quán sắp xếp bàn thế nào.

Giờ sang hệ thống. 200 request mỗi giây đến, mỗi request ở lại nửa giây, thì trung bình có 100 request đang nằm trong hệ thống.

Cái hay là định luật này đúng cho mọi hệ thống ổn định. Không cần biết bên trong cài đặt thế nào, không cần giả định về phân phối hay scheduling. Khi đang xử lý sự cố, queue depth và request rate thường dễ đọc hơn latency percentile. Từ hai con số đó mình suy ra W, hoặc từ hai con số khác suy ra con số còn lại.

Giờ áp vào connection pool, vì nó liên quan thẳng tới WorkOS. Đây là số minh họa. Pool có 20 connection. Mỗi query mất 50 mili giây. Hệ thống nhận 300 request mỗi giây, mỗi request một query. Little nói: 300 nhân 0,05 là 15, tức trung bình có 15 connection đang bận. Còn dư 5, ổn.

Giờ database chậm đi gấp đôi, query mất 100 mili giây, tải vẫn 300. Little nói: 300 nhân 0,1 là 30 connection cần dùng, nhưng pool chỉ có 20. Không đủ. Hay nhìn kiểu khác: 20 connection, mỗi query 100 mili giây, thì tối đa phục vụ được 200 request mỗi giây, mà tải đến là 300. Hàng đợi sẽ dài ra mãi cho tới khi có ai đó bỏ cuộc. Một con số thay đổi gấp đôi, và hệ thống từ dư dả thành không đủ.

Nhưng có một cảnh báo: định luật chỉ nói về trung bình. Muốn biết tail latency, tức những request chậm nhất, thì phải đo riêng.

## 5. Đường cong hockey stick (2:30)

**Người nói: Người 1**

[Chỉ vào đồ thị.] Câu hỏi tiếp theo: khi tải tăng, hàng đợi tăng thế nào? Với mô hình đơn giản nhất, một server, request đến ngẫu nhiên, công thức là L bằng rho chia một trừ rho. Rho là mức sử dụng, tức phần trăm thời gian server bận.

Nhìn đồ thị. Ở 70% tải, L khoảng 2,3. Hàng đợi nhỏ, hệ thống ổn. Lên 90%, L bằng 9, gấp khoảng bốn lần. Lên 95%, L bằng 19. Lên 99%, L bằng 99. Đường cong gần như phẳng rồi bỗng vọt lên. Đó là lý do gọi là hockey stick, cây gậy khúc côn cầu.

Nói theo thời gian chờ cho dễ cảm nhận. Giả sử mỗi request mất 50 mili giây để xử lý, đây là số minh họa. Ở 90% tải, thời gian một request ở trong hệ thống khoảng 500 mili giây, gấp mười lần thời gian xử lý. Ở 95%, khoảng một giây. Ở 99%, khoảng năm giây. Từ 90% lên 99% tải, tức tăng chưa tới mười phần trăm, mà độ trễ tăng mười lần.

Một hình ảnh quen thuộc: đường cao tốc. Xe chạy 70% công suất thì mọi người đi mượt. Lên tới gần kín, chỉ cần một người đạp phanh nhẹ là cả làn dừng lại, và sóng dừng đó lan ngược về sau cả vài chục phút, dù người đạp phanh đã đi mất từ lâu. Mình sẽ quay lại hình ảnh này vì nó chính là metastable.

Ý nghĩa thực tế: con người quen nghĩ tuyến tính. 95% tải nghe như "còn dư 5%". Thực tế là sắp nổ. Ngoài ra, nhiều công cụ báo động đặt ở 80% hoặc 90% CPU, nhưng CPU không phải là mức sử dụng của queue, nên con số đó chỉ là tín hiệu gần đúng.

Lưu ý trung thực: đây là mô hình M/M/1, giả định request đến theo phân phối Poisson và thời gian xử lý theo phân phối mũ. Traffic thật bursty hơn, nên điểm gãy thường đến sớm hơn. Mình tin vào hình dạng đường cong, không tin vào con số tuyệt đối.

[Hỏi khán phòng.] Hệ thống của các bạn đang ở đâu trên đường cong này? Và các bạn có biết con số đó, hay đang đoán?

## 6. Bài học 01 (1:00)

**Người nói: Người 1**

Bài học đầu tiên: gần đầy là sắp nổ. Ba phản ứng thực tế. Một, để dành headroom. Chạy ở 60 đến 70% thay vì 90% nghe lãng phí, nhưng đó là tiền bảo hiểm cho đoạn dốc của đường cong. Hai, áp backpressure, tức để tầng dưới nói được với tầng trên rằng "đủ rồi, đừng gửi nữa", thay vì cứ nhận hết rồi xếp hàng vô tận. Ba, shed load trước khi chạm ngưỡng: thà từ chối rõ ràng một phần request còn hơn để tất cả đều chậm.

Queue cho mình biết hệ thống mong manh ở đâu. Nhưng nó chưa nói vì sao hệ thống lại dao động. Phần sau sẽ trả lời.

## 7. Delay mở phần (1:00)

**Người nói: Người 1**

Phần hai. Mình đặt một câu hơi ngược: phản ứng nhanh hơn có thể tệ hơn.

Ai từng tắm vòi nước nóng lạnh ở nhà trọ chắc hiểu. Mình vặn nóng thêm, nước chưa kịp nóng vì ống còn nước lạnh. Mình vặn tiếp. Rồi nước nóng ập tới, bỏng, mình vặn mạnh về phía lạnh, và lại chờ. Không ai ngu cả. Cái làm mình dao động là khoảng trễ giữa hành động và kết quả, cộng với việc mình điều khiển bằng thông tin cũ.

Trong cuốn Thinking in Systems, Donella Meadows nói delay trong feedback loop là nguyên nhân phổ biến của dao động và overshoot. (kiểm tra: mình dựa vào bản tóm tắt, chưa đối chiếu sách gốc, nên nói "phổ biến", đừng nói "luôn luôn".)

## 8. Đại lý xe (2:00)

**Người nói: Người 1**

Ví dụ của Meadows cho dễ hình dung. Một đại lý xe thấy bán chạy. Họ đặt thêm xe, nhưng hơi do dự vì không chắc xu hướng có bền không. Xe đến sau một khoảng sản xuất và vận chuyển. Lúc xe về, nhu cầu đã đổi, tồn kho dư. Họ hoảng, cắt đơn quá tay. Rồi lại thiếu xe, và vòng lặp quay lại bước một.

[Chỉ vào thẻ tối.] Thủ phạm là cái delay ở giữa. Người ra quyết định đang điều khiển bằng thông tin cũ. Họ nhìn tồn kho hôm nay, nhưng quyết định của họ chỉ có tác dụng sau vài tuần.

Có một ví dụ nổi tiếng cùng họ: trò chơi Beer Game ở MIT, do Jay Forrester và sau này John Sterman phát triển. Mỗi người chơi là một mắt xích trong chuỗi cung ứng bia, từ nhà bán lẻ tới nhà máy, đặt hàng với nhau và có độ trễ giao hàng. Kết quả hay lặp lại là đơn hàng dao động ngày càng mạnh khi đi ngược lên chuỗi, dù nhu cầu thật của người uống bia gần như không đổi. Người chơi thường thông minh và có thiện chí, vậy mà vẫn thế. (kiểm tra: mình nhớ lại từ tài liệu về Beer Game, chưa đối chiếu nguồn gốc, nên kể ở mức tổng quát và đừng nêu con số.)

Hai thẻ dưới của slide: phản ứng nhanh trên ít thông tin thì biên độ dao động lớn hơn. Phản ứng chậm hơn thì ổn định hơn, nhưng quá chậm thì cứng nhắc, không bắt kịp thay đổi thật.

[Hỏi.] Nhóm của bạn có "đặt thêm xe" kiểu nào không? Tuyển người cho một dự án rồi dự án đổi hướng, mua thêm capacity rồi tháng sau dư? Đó là cùng một vòng lặp.

## 9. Kubernetes HPA (2:00)

**Người nói: Người 1**

Phiên bản kỹ thuật của chuyện này là HPA flapping trong Kubernetes. HPA là Horizontal Pod Autoscaler, thứ tự động tăng giảm số pod theo metric. Hình dung: metric vượt ngưỡng, HPA scale up. Pod mới khởi động mất một lúc, mình cũng đang có delay ở đây. Khi pod mới sẵn sàng, tải mỗi pod giảm, metric xuống dưới ngưỡng, HPA scale down. Capacity giảm, tải mỗi pod tăng lại, metric vượt ngưỡng. Cứ thế lặp trong vài phút, pod sinh ra rồi bị giết liên tục.

Cách chữa có sẵn là cửa sổ ổn định, stabilization window. Mặc định, scale down có cửa sổ 300 giây, scale up là 0 giây. Nghĩa là scale up nhanh, scale down thận trọng. Trong lúc scale down, HPA không đưa số pod xuống dưới mức khuyến nghị cao nhất trong cửa sổ đó. Đây chính là damping, thêm quán tính để hệ thống không giật theo từng nhiễu nhỏ. Lý do chọn bất đối xứng: thiếu capacity gây hại ngay, còn dư capacity chỉ tốn tiền.

Nhưng damping không miễn phí. Quá nhiều damping thì hệ thống chậm: một đợt tải thật tăng lên mà hệ thống vẫn còn đang "chờ cho chắc". Tune là cân bằng giữa tốc độ phản ứng và độ ổn định, và không có giá trị đúng cho mọi hệ thống.

Một lưu ý cho mọi người: ở slide sau mình sẽ nói retry, và retry cũng là một cơ chế phản hồi có độ trễ. Hãy nhớ hình ảnh vòng lặp scale up, scale down này.

[Bàn giao cho Người 2.] Delay cho mình thấy vì sao một hệ thống dao động, kể cả khi mọi người đều có ý tốt. Giờ Người 2 sẽ cho mình xem cùng một cơ chế lặp lại ở những sự cố thật, từ cache cho tới database.

## 10. Catalog: khung chung (1:00)

**Người nói: Người 2**

[Nhận từ Người 1.] Cảm ơn bạn. Mình nối tiếp ngay chỗ bạn vừa dừng: delay làm hệ thống dao động, nhưng điều gì xảy ra khi hệ thống bắt đầu lỗi và mọi client đồng loạt thử lại?

Phần ba. Retry storm có họ hàng. Mình dùng một khung bốn bước cho tất cả, để mỗi lần nghe một sự cố mới mọi người có thể tự đặt câu hỏi.

Bước một, trigger: một sự kiện tạm thời. Một đợt traffic, một lần deploy, một đường mạng chập chờn. Bước hai, khuếch đại: mỗi lỗi sinh thêm việc, ví dụ mỗi request lỗi sinh ra một lần retry. Bước ba, loop duy trì: việc thêm làm hệ thống chậm thêm, chậm sinh lỗi, lỗi sinh việc, và vòng cứ quay dù trigger đã hết. Bước bốn, cách phá loop: thứ gì làm đứt một mắt xích của vòng.

Ba họ hàng hôm nay: cache stampede, connection pool, và một nhóm các biến thể khác gồm GC death spiral và reconnect storm. Chú ý là mỗi họ hàng đều có điểm chung: cái bị cạn khác nhau, nhưng hình dạng vòng lặp thì giống nhau.

## 11. Cache stampede (1:30)

**Người nói: Người 2**

Cache stampede: một key nóng hết TTL. Hàng loạt request cùng miss. Tất cả cùng recompute, đập vào backend. Backend chậm đi, key lâu có lại, càng nhiều request miss. Cache vốn sinh ra để che tải, và khi nó mất thì tải thật hiện ra đột ngột.

Dấu hiệu để nhận ra: tải có chu kỳ theo TTL. Ví dụ một query chạy hàng trăm lần mỗi giây với TTL 60 giây, đến lúc hết hạn, hàng chục query giống nhau chạy cùng lúc trong vài mili giây. Nếu dashboard của bạn có những gai đều đặn mỗi 60 giây, đáng nghi.

Ba cách phá: TTL jitter để các key không hết hạn cùng lúc, ví dụ TTL 60 giây cộng một số ngẫu nhiên từ 0 đến 10. Single-flight, chỉ một request đi recompute, số còn lại chờ kết quả của nó. Và làm mới ngẫu nhiên trước khi hết hạn, một kỹ thuật tên XFetch.

Một case gần hơn: StrongDM, ngày 1/6/2024. Sau khi nâng cấp database, khách hàng reconnect ồ ạt và gây thundering herd. Họ rollback, nhưng dịch vụ vẫn chậm thêm một lúc. Nói cho chính xác: đây là reconnect storm chứ không phải cache expiry cổ điển, nhưng cơ chế như nhau.

## 11b. Facebook 2010: hệ thống tự sửa làm hỏng thêm (2:00)

**Người nói: Người 2**

[Slide `case-facebook`.]

Một case lớn và kinh điển: Facebook, ngày 23/9/2010. Site bị gián đoạn khoảng hai tiếng rưỡi, mà Facebook gọi là sự cố tệ nhất của họ trong hơn bốn năm. Họ có một hệ thống tự động kiểm tra giá trị config. Nếu giá trị trong cache bị coi là sai, nó thay bằng bản lấy từ kho lưu trữ chính. Cách này ổn khi lỗi nằm ở cache. Nhưng hôm đó có người đổi giá trị config trong chính kho lưu trữ, hệ thống kiểm tra coi giá trị mới là sai, và mọi client đồng loạt chạy đi sửa bằng cách hỏi một cụm database. Cụm đó nhận hàng trăm nghìn query mỗi giây.

Chỗ đáng sợ là vòng lặp: client nhận lỗi từ database thì coi đó là giá trị không hợp lệ và xóa key trong cache, rồi lại hỏi database. Database càng lỗi, càng bị hỏi. Chính Facebook viết rằng họ đã rơi vào một feedback loop không cho database hồi phục. Ngay cả khi nguyên nhân ban đầu đã được sửa, cơn lũ query vẫn tiếp diễn. Cuối cùng họ phải chặn toàn bộ traffic tới cụm đó, tức là chủ động đưa cả site ngoại tuyến, chờ database hồi phục rồi mới cho người dùng vào lại từ từ. Họ cũng tắt luôn hệ thống tự sửa config.

Hãy để ý hai điều. Thứ nhất, đây đúng là hai khái niệm: một lần đổi config là trigger, và vòng "lỗi database sinh thêm query" là thứ duy trì sự cố. Thứ hai, thứ làm hại là một cơ chế tự chữa, được viết ra để tăng độ tin cậy. (Nguồn: bài "More Details on Today's Outage" của Facebook Engineering.)

## 12. Connection pool (2:00)

**Người nói: Người 2**

Quay lại WorkOS, vì nó chính là loại này, và mình đã giải thích cơ chế ở slide trước. Request giữ một connection để chờ connection thứ hai, nên hầu hết connection bị chiếm mà không việc nào hoàn thành. Chỗ này nói nhanh, đừng lặp lại phần code. Cái cần nhấn là kết luận: pool cạn không phải do thiếu connection, mà do connection bị giữ vô ích.

Hai case nữa, để thấy WorkOS không phải ngoại lệ. Val Town: một query deadlock chiếm slot trong pool, và pool không có query timeout, nên slot đó không bao giờ được trả. Gorgias: họ đã có pool và proxy, tức đã làm đúng những việc người ta khuyên, nhưng một edge case về timeout vẫn gây lockup, và dọn backlog mất thêm khoảng một giờ. Bài học: có pool chưa đủ, phải có timeout ở mọi chỗ chờ.

Cách phá: borrow timeout ngắn, query timeout, giới hạn concurrency. Dòng cuối của slide, "không giữ connection khi chờ connection khác", là bài học mình tự rút ra từ case WorkOS, không phải lời của họ. Còn các biện pháp họ tự nêu trong postmortem: dùng lại connection đang giữ thay vì mở cái mới, kèm savepoint để cô lập lỗi. Rút ngắn borrow timeout. Hủy request quá hạn để nhả resource. Giới hạn concurrency. Và rà soát các nested transaction khác trong hệ thống.

[Hỏi khán phòng.] Ai trong phòng biết borrow timeout của pool chính của mình là bao nhiêu? Nếu mặc định là 30 giây thì với một sự cố kiểu WorkOS, 30 giây là rất lâu.

## 12b. GC death spiral và reconnect storm (2:00)

**Người nói: Người 2**

Họ hàng thứ ba. Cùng khung bốn bước, nhưng resource bị cạn không phải connection mà là heap, port hoặc luồng xử lý.

GC death spiral của Cassandra: heap bị ép, pause GC dài ra, node bị các node khác đánh dấu DOWN. Các node còn lại phải gánh thêm và client retry, nên áp lực lên heap tăng, pause càng dày. Mỗi vòng làm vòng sau tệ hơn. Mấu chốt: lúc node đang pause GC thì nó không phản hồi, nên nó bị coi là chết, và việc coi nó là chết làm các node còn lại nặng thêm.

Bluesky, tháng 4/2026, là postmortem thật: handler RPC không giới hạn concurrency, nên khi tải tăng thì cạn port và log bị nghẽn, rồi AppView crash lặp. Cam kết khắc phục của họ gồm concurrency limit bắt buộc cho mọi RPC handler và đưa log lỗi khối lượng lớn ra khỏi lời gọi chặn. Điểm thú vị là log. Khi hệ thống lỗi thì log lỗi tăng, và nếu việc ghi log chặn luồng chính thì chính việc ghi lỗi làm hệ thống chậm thêm. Một cơ chế quan sát biến thành một mắt xích của vòng lặp.

Reconnect storm của MongoDB và CockroachDB: một election hoặc failover xảy ra, mọi driver reconnect cùng một lúc. Retry không có jitter giữ các client đồng bộ với nhau, nên đợt reconnect sau lại đập vào đúng điểm đó. Hình dung hàng nghìn client cùng nhìn đồng hồ và cùng thử lại sau đúng một giây.

Cách phá: backoff có jitter, concurrency limit, và log không chặn luồng chính.

Nói rõ nguồn: Cassandra và MongoDB/CockroachDB là guide của vendor Netdata, không phải postmortem. Bluesky mình đọc qua bản tóm tắt của ilert. (kiểm tra: đọc bản gốc của Bluesky trước khi nói chi tiết.)

## 13. Ba trạng thái metastable (2:00)

**Người nói: Người 2**

Phần cuối, cao trào. Một bài báo năm 2021 của Bronson và cộng sự mô tả một hệ thống có ba trạng thái.

Stable: tải thấp, tự hồi phục sau overload tạm thời. Mình bơm một đợt tải, hệ thống chậm đi, rồi tự về lại bình thường. Vulnerable: tải cao, vẫn ổn nếu không có overload tạm thời. Phần lớn hệ thống production nằm ở đây, vì ta tối ưu cho trường hợp thường gặp, ví dụ cache che đi tải thật, hoặc ta chạy ở 85% công suất vì "vẫn ổn mà". Trông bình thường, nhưng một cú đẩy nhỏ là sang trạng thái kế. Metastable: overload tự duy trì sau khi trigger đã hết. Throughput vẫn còn, nghĩa là server vẫn bận, nhưng goodput, tức việc hữu ích hoàn thành, gần như bằng không.

Hai khái niệm cần nhớ: trigger là sự kiện tạm thời gây overload. Sustaining effect là cơ chế khuếch đại giữ hệ thống chết khi trigger đã hết.

Điểm mình muốn nhấn: nguyên nhân gốc theo kiểu truyền thống, tức trigger, và nguyên nhân duy trì sự cố là hai thứ khác nhau. Postmortem hay dừng ở trigger, vì trigger dễ chỉ tay vào: một lần deploy, một đợt traffic, một lần đổi config. Nhưng cùng một trigger, hệ thống ở trạng thái stable thì qua được, hệ thống ở trạng thái vulnerable thì sập. Vậy cái đáng sửa là trạng thái vulnerable và cơ chế duy trì, chứ không phải chỉ trigger.

## 13b. AWS DynamoDB 2015: không thể thêm capacity (2:00)

**Người nói: Người 2**

[Slide `case-aws`.]

Ví dụ thứ hai để thấy mô hình này không chỉ của WorkOS và Facebook. AWS, ngày 20/9/2015, DynamoDB ở US-East. Lúc 2 giờ 19 sáng giờ PDT, một sự cố mạng ngắn ảnh hưởng một phần storage server. Các server đó hỏi metadata service để lấy lại danh sách membership. Nhưng vì khách hàng dùng ngày càng nhiều tính năng Global Secondary Indexes, danh sách đó đã phình to, nên phản hồi mất lâu hơn thời gian cho phép. Server lấy membership không kịp thì tự gỡ mình khỏi vòng nhận request, rồi retry. Nhiều server cùng hỏi những danh sách lớn cùng lúc làm metadata service chậm thêm, kéo theo cả những server không liên quan tới sự cố mạng ban đầu cũng không lấy kịp. Tới 2 giờ 37, tỉ lệ lỗi của khách hàng khoảng 55%.

Đáng nói nhất là phần khắc phục. Đội AWS không thể thêm capacity cho metadata service, vì nó quá tải đến mức không xử lý nổi cả request quản trị. Lúc 5 giờ 06 họ chọn tạm dừng toàn bộ request tới metadata service để cắt retry, rồi mới thêm được capacity và cho tải trở lại. Khoảng 7 giờ 10, tỉ lệ lỗi mới đủ thấp cho đa số khách hàng, tức gần năm tiếng sau khi bắt đầu. Mỗi mắt xích: trigger là sự cố mạng ngắn, vulnerable là metadata service thiếu capacity cho membership đã phình, sustaining effect là retry và các server khỏe bị kéo theo. Phá loop bằng cách cắt tải thay vì thêm tải. (Nguồn: bản tóm tắt sự cố DynamoDB của AWS, aws.amazon.com/message/5467D2.)

## 14. Số liệu thực tế (1:00)

**Người nói: Người 2**

Metastable không hiếm. Một nghiên cứu năm 2022 tại OSDI xem xét 22 sự cố từ 11 tổ chức. Họ cũng ghi nhận ít nhất 4 trong 15 outage lớn của AWS trong một thập kỷ qua thuộc loại này.

Theo slide của tác giả, khoảng 45% trigger là lỗi của kỹ sư, như config sai hay deploy lỗi, và khoảng 35% là load spike. Với sustaining effect, hơn một nửa là tải tăng do retry. (kiểm tra: ba tỷ lệ này lấy từ slide của tác giả, cần đối chiếu bảng trong paper. Slide ghi 21 sự cố còn paper ghi 22.) Nếu chưa kiểm tra, hãy nói "khoảng một nửa" và nói rõ nguồn.

Điểm đáng rút ra: trigger đa dạng, nhưng cơ chế duy trì thì lặp lại, và retry nằm đầu bảng. Nên đầu tư phòng thủ vào sustaining effect có lợi hơn đoán trước mọi trigger.

## 15. Retry storm bằng con số (2:30)

**Người nói: Người 2**

[Đi chậm, từng bước.] Hệ thống chịu được 100 request mỗi giây. Tải bình thường 80, ổn, còn dư 20%. Một trigger: database chậm vài giây, request bắt đầu timeout. Client retry, nên tải thực tế thành 80 request mới cộng 80 retry, 160 request mỗi giây. Vượt capacity.

Bước cuối là điều quan trọng nhất. Database đã hết chậm từ lâu, trigger đã biến mất. Nhưng 160 vẫn lớn hơn 100. Và phần lớn request mà server đang xử lý là retry của những request client đã bỏ rơi. Client không còn chờ câu trả lời nữa, nên server làm việc vô ích. Goodput gần bằng không.

Restart cũng không giúp, vì client vẫn đang retry, tải ập vào ngay. Cái làm mình sốc là hệ thống "khỏe" ở 80 tải bình thường, và "chết" ở cùng 80 tải đó, chỉ khác là có một lịch sử lỡ nhịp ở giữa. Đây là tính chất của hệ thống có trạng thái: cùng một đầu vào, đầu ra khác nhau tùy hệ thống đã từng ở đâu.

Giờ nói tới nhân tố bị bỏ quên: retry nhân lên theo từng tầng. Giả sử một request đi qua năm tầng service, mỗi tầng thử tối đa 3 lần khi lỗi. Ở trường hợp xấu nhất, tầng cuối nhận 3 mũ 5, tức 243 lần tải bình thường, từ một request ban đầu. Nếu mỗi tầng chỉ thử tối đa 2 lần, thì là 2 mũ 5, 32 lần. Cái này là tính toán cho trường hợp xấu nhất, không phải số đo, nhưng nó cho thấy vì sao một cấu hình retry nghe hợp lý ở từng tầng lại nguy hiểm khi ghép lại. Mỗi người viết service chỉ thấy tầng của mình.

Hình ảnh để nhớ: một ngã tư kẹt cứng. Xe chết máy gây ra kẹt đã được kéo đi, nhưng các xe còn lại chặn nhau nên ngã tư vẫn kẹt. Ở đây những chiếc xe đó chính là retry.

Lưu ý: số liệu ở đây là giả định để minh họa.

## 16. Vẽ loop trước khi chữa (1:30)

**Người nói: Người 2**

[Mời khán phòng tự điền mũi tên trước khi lộ đáp án.] Mọi thứ vừa kể có thể vẽ thành hai loại vòng lặp. Cách vẽ: ghi các biến lên giấy, rồi nối bằng mũi tên, ghi chiều tác động. Mình gọi là causal loop diagram.

Loop R, reinforcing, tự khuếch đại: latency tăng thì timeout tăng, timeout tăng thì retry tăng, retry tăng thì load tăng, và load tăng lại làm latency tăng tiếp. Quay một vòng thì mọi thứ tệ hơn một chút. Đó là vòng của WorkOS, của Facebook, của AWS ở trên.

Loop B, balancing, tự kéo hệ thống về: load tăng thì shed bớt request, request bị shed làm load giảm. Một vòng thì mọi thứ ổn hơn.

Metastable xảy ra khi R thắng B. Vì vậy chữa bệnh nghĩa là thêm một balancing loop đủ mạnh để thắng loop R, chứ không phải chỉ vá chỗ vừa hỏng. Mỗi công cụ ở phần sau, như backoff, shedding và các giới hạn, là một cách làm B mạnh lên hoặc làm R yếu đi.

Mẹo thực tế: lần sau xử lý sự cố, trước khi hỏi "ai làm hỏng", hãy lấy giấy vẽ loop. Chỉ cần ba bốn biến là thấy ngay mắt xích nào dễ cắt nhất.

## 17. Phá loop (3:00)

**Người nói: Người 2**

Ba nguyên tắc. Một, giảm tải khi lỗi: load shedding, retry budget, hàng đợi có giới hạn. Hai, giới hạn mọi thứ: retry, queue, concurrency, connection. Ba, jitter mọi thứ: backoff, TTL, reconnect.

Giờ cụ thể từng cái. Backoff cộng jitter: lần retry đầu chờ ngẫu nhiên trong khoảng 0 đến 100 mili giây, lần hai 0 đến 200, lần ba 0 đến 400, cứ nhân đôi tới một mức trần, ví dụ mười giây. Phần ngẫu nhiên quan trọng hơn phần nhân đôi, vì nó làm các client không đập vào server cùng lúc. Đây là số minh họa.

Retry budget: thay vì mỗi request được thử lại ba lần, đặt tổng số retry không vượt một tỷ lệ nhỏ của tổng traffic, ví dụ 10%. Khi hệ thống khỏe, hầu như không ai chạm giới hạn. Khi hệ thống đang lỗi hàng loạt, ngân sách hết nhanh và retry dừng, nên không còn nhân tải lên nữa. Đó chính là cách làm yếu loop R.

Load shedding: khi hàng đợi vượt ngưỡng thì từ chối request mới ngay, trả lỗi rõ ràng, thay vì nhận vào rồi để chết trong hàng đợi. Với người dùng, "thử lại sau" nhanh còn hơn một vòng xoay hai mươi giây rồi lỗi.

Và đôi khi cách phá loop là cắt hẳn tải, như đã thấy ở hai case lớn. Facebook chặn toàn bộ traffic tới cụm database, AWS tạm dừng request tới metadata service. Cả hai đều chấp nhận một khoảng thời gian chết có chủ đích để hệ thống thoát khỏi vòng. Cái đó cần được thiết kế sẵn: nếu bạn chưa bao giờ nghĩ tới nút "ngắt tải", lúc có sự cố sẽ không kịp.

Một cảnh báo: mỗi công cụ là một balancing loop mới, và tune sai thì chính nó thành trigger. DoorDash có một case: một circuit breaker cấu hình sai đã cắt traffic giữa nhiều service không liên quan. (kiểm tra: đối chiếu chi tiết với bài gốc của DoorDash trước khi kể sâu hơn.)

Và nói thẳng về giới hạn: các tác giả gốc thừa nhận chưa có cách có hệ thống để xây hệ thống chống mọi metastable failure chưa biết. Có hướng đi, ví dụ Amazon đề xuất dùng performance model để dự đoán điều kiện vulnerable, nhưng đó vẫn là vấn đề mở. Một nghiên cứu khác, SREcon 2025, còn chỉ ra chính hành động recovery cũng có thể gây ra sự cố lớn hơn. AWS 2015 là một ví dụ: họ không thể thêm capacity vì dịch vụ quá tải không xử lý nổi request quản trị.

[Bàn giao lại cho Người 1.] Mình trả lại cho Người 1 để quay về câu hỏi đầu buổi.

## 18. Bốn điều mang về (1:00)

**Người nói: Người 1**

[Nhận lại từ Người 2.] Cảm ơn bạn. Mình gom lại thành bốn điều.

Một, hỏi "cái gì đang duy trì sự cố", đừng chỉ hỏi "cái gì gây ra nó". Trigger thì mỗi lần một khác, còn cơ chế duy trì thì lặp lại.

Hai, retry là load, hãy tính nó vào capacity. Nếu hệ thống chỉ đủ 100 mà bạn cho phép client retry vô hạn, thì capacity thực của bạn thấp hơn 100 lúc cần nhất.

Ba, hệ thống tối ưu cho trường hợp thường gặp thường là hệ thống vulnerable. Cache, headroom mỏng, pool vừa đủ: tất cả đều ổn cho tới khi không ổn.

Bốn, recovery cũng cần được thiết kế, test và có giới hạn. Nút ngắt tải, cách thêm capacity khi hệ thống đang quá tải, runbook cho trường hợp "restart không giúp": những thứ đó nên có trước khi cần.

Quay lại câu hỏi đầu buổi: cái giữ WorkOS ở trạng thái chết là một vòng lặp tự duy trì, không phải một lỗi. Và đó cũng là câu trả lời cho Facebook năm 2010 và AWS năm 2015.

## 19. Cầu sang Session B (1:00)

**Người nói: Người 1**

Mình kết bằng một câu hỏi, và cũng là câu mở đầu của Session B: retry policy này do ai viết, và KPI nào ép họ? Mỗi giá trị retry, mỗi timeout, mỗi mức headroom đều là kết quả của một quyết định, và các quyết định đó nằm trong một tổ chức có áp lực, có deadline, có người được thưởng vì ship nhanh và không ai được thưởng vì để dư capacity.

Cùng một loop, nhìn ở tầng con người và tổ chức. Cảm ơn mọi người. Mình sẵn sàng nhận câu hỏi.

---

## Tổng thời gian ước tính

Khoảng 40 phút nếu nói đủ hết, chưa tính hỏi đáp. Nếu thiếu giờ, cắt theo thứ tự: bỏ mục 12b (GC death spiral), rút mục 14 (số liệu thực tế) còn một câu, bỏ phần Beer Game ở mục 8, bỏ mục 11b (Facebook) hoặc mục 13b (AWS), giữ một trong hai, rút mục 8 và 9 còn một ví dụ.

## Câu hỏi dự kiến

**Khác gì cascading failure thông thường?**
Cascading failure là một chuỗi lỗi lan sang các service khác. Metastable là trường hợp đặc biệt, bền vững: hệ thống không tự hồi phục sau khi trigger đã biến mất, vì có sustaining effect giữ nó lại.

**Retry rõ ràng có ích, sao lại thành vấn đề?**
Retry giúp khi lỗi thoáng qua và độc lập. Nó gây hại khi lỗi do quá tải, vì nó biến thành thêm tải đúng lúc hệ thống yếu nhất. Cần backoff, jitter, giới hạn số lần và retry budget.

**Làm sao biết hệ thống mình đang ở trạng thái vulnerable?**
Load test để tìm ngưỡng gãy, theo dõi mức sử dụng so với đường cong, và thử chaos experiment tạo một trigger giả để xem hệ thống có tự hồi phục không. Đây là hướng gợi ý, không phải quy trình chuẩn từ nguồn.

**Circuit breaker có giải quyết được không?**
Nó giúp, nhưng tune sai thì chính nó thành trigger, như case DoorDash. Nó là một balancing loop mới, cần được thiết kế và test như mọi thứ khác.

**Retry budget đặt bao nhiêu là hợp lý?**
Không có con số đúng cho mọi hệ thống. Ví dụ 10% trong bài chỉ để minh họa. Quá nhỏ thì mất lợi ích của retry với lỗi thoáng qua, quá lớn thì khi lỗi hàng loạt vẫn nhân tải lên nhiều lần. Cách làm: bắt đầu nhỏ, quan sát tỉ lệ lỗi thoáng qua thực tế rồi chỉnh.

**Thêm capacity có chữa được không?**
Thường không, hoặc không kịp. Ở WorkOS, thêm capacity không giúp, vì connection bị giữ vô ích chứ không phải thiếu. Ở AWS 2015, họ còn không thể thêm capacity vì dịch vụ quá tải không nhận nổi request quản trị. Capacity giúp ở trạng thái vulnerable (đẩy ngưỡng gãy ra xa), ít giúp khi đã ở metastable.

**Làm sao tránh bug kiểu "nested transaction xin connection thứ hai"?**
Không có cách chắc chắn ở tầng code review. Hướng thực tế: giới hạn số connection một request được giữ, đặt borrow timeout ngắn, đo số connection bị giữ trên mỗi request, và có test với pool nhỏ để lộ hold-and-wait sớm. Đây là gợi ý của mình, không phải quy trình từ postmortem.

**Có cách nào đo độ "vulnerable" mà không đợi sự cố?**
Đo headroom (mức dùng so với ngưỡng gãy), đo bao nhiêu phần tải đang được cache che, và thử tiêm lỗi: tăng độ trễ của một dependency vài giây trên môi trường staging rồi xem hệ thống có tự hồi phục không. Đây là hướng gợi ý, chưa có phương pháp chuẩn.

## Kiểm tra trước buổi nói

1. Số liệu OSDI (mục 14) so với paper.
2. Đọc bản gốc postmortem của Bluesky nếu định nhắc đến.
3. Đối chiếu câu của Meadows với sách gốc, và kể Beer Game ở mức tổng quát nếu chưa kiểm.
4. Đọc lại bản gốc của DoorDash nếu định kể thêm chi tiết.
5. Đọc lại hai nguồn mới: bài Facebook Engineering ngày 23/9/2010 và bản tóm tắt DynamoDB của AWS (aws.amazon.com/message/5467D2) để chắc về các con số trước khi nói.
6. Tập nói to một lần và bấm giờ.
