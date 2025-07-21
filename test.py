import telethon.tl.types as types

report_reasons = [attr for attr in dir(types) if attr.startswith('InputReportReason')]
print("Доступные причины жалоб:")
for reason in report_reasons:
    print(reason)
